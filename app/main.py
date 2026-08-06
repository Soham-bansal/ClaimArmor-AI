from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date
from pathlib import Path

from app.config import load_local_env

load_local_env()

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.responses import Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except ImportError:
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4"

    class _NoopMetric:
        def labels(self, *_args): return self
        def inc(self): return None
        def observe(self, _value): return None

    def Counter(*_args, **_kwargs): return _NoopMetric()
    def Histogram(*_args, **_kwargs): return _NoopMetric()
    def generate_latest():
        return b"# ClaimArmor metrics require the optional prometheus-client package.\nclaimarmor_up 1\n"

from app import db
from app.auth import authenticate, current_user, issue_token, require_roles, seed_users
from app.evaluation import load_evaluation
from app.ml.runtime import metrics as model_metrics
from app.services.business import simulate_roi
from app.services.policy import evaluate_retrieval, extract_pdf_text, get_index, validate_policy_record
from app.schemas import ClaimInput, CsvUploadRequest, EdiUploadRequest, LoginRequest, PolicyIngestRequest, ReviewRequest, RoiAssumptions, StreamSimulationRequest
from app.services.ingestion import parse_synthetic_837
from app.seed import DEMO_CLAIMS
from app.services.pipeline import investigate, investigate_events


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    seed_users()
    for raw_claim in DEMO_CLAIMS:
        claim = ClaimInput.model_validate(raw_claim).model_dump(mode="json")
        if not db.get_claim(claim["claim_id"]):
            db.put_claim(claim)
            db.append_audit(claim["claim_id"], "CLAIM_INGESTED", {"source": "synthetic_seed"})
    yield


app = FastAPI(title="ClaimArmor AI", version="0.1.0", lifespan=lifespan)
react_dist = Path(__file__).parent / "static" / "react"
if react_dist.exists():
    app.mount("/react", StaticFiles(directory=react_dist, html=True), name="react-dashboard")
try:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)
except ImportError:
    # Observability remains optional for the lightweight local install.
    pass
logger = logging.getLogger("claimarmor")
login_attempts: dict[str, deque[float]] = defaultdict(deque)
REQUESTS = Counter("claimarmor_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("claimarmor_http_request_duration_seconds", "HTTP request duration", ["method", "path"])


@app.middleware("http")
async def operational_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))[:80]
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    REQUESTS.labels(request.method, request.url.path, str(response.status_code)).inc()
    LATENCY.labels(request.method, request.url.path).observe(duration_ms / 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/docs"):
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; script-src 'self' https://cdn.jsdelivr.net; connect-src 'self'; img-src 'self' data: https://fastapi.tiangolo.com"
    else:
        response.headers["Content-Security-Policy"] = "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:"
    if request.url.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    logger.info("request method=%s path=%s status=%s duration_ms=%s request_id=%s", request.method, request.url.path, response.status_code, duration_ms, request_id)
    return response


@app.get("/metrics", include_in_schema=False)
def prometheus_metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/api/health")
def health() -> dict:
    return {"status": "healthy", "version": app.version, "data_classification": "SYNTHETIC_ONLY", "storage": db.storage_info()}


@app.post("/api/auth/login")
def login(request: LoginRequest, http_request: Request) -> dict:
    client = http_request.client.host if http_request.client else "unknown"
    now = time.time()
    attempts = login_attempts[client]
    while attempts and attempts[0] < now - 60:
        attempts.popleft()
    if len(attempts) >= 10:
        raise HTTPException(429, "Too many login attempts; retry after one minute")
    attempts.append(now)
    user = authenticate(request.username, request.password)
    if not user:
        raise HTTPException(401, "Invalid username or password")
    return {"access_token": issue_token(user), "token_type": "bearer", "user": user}


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)) -> dict:
    return user


@app.get("/api/claims")
def claims(_: dict = Depends(require_roles("ANALYST", "REVIEWER", "AUDITOR"))) -> list[dict]:
    return db.list_claims()


@app.post("/api/claims", status_code=201)
def create_claim(claim: ClaimInput, user: dict = Depends(require_roles("ANALYST"))) -> dict:
    if db.get_claim(claim.claim_id):
        raise HTTPException(409, "A claim with this ID already exists")
    payload = claim.model_dump(mode="json")
    db.put_claim(payload)
    db.append_audit(claim.claim_id, "CLAIM_INGESTED", {"source": "api", "actor": user["username"]})
    return payload


@app.post("/api/claims/upload-csv")
def upload_claim_csv(request: CsvUploadRequest, user: dict = Depends(require_roles("ANALYST"))) -> dict:
    reader = csv.DictReader(io.StringIO(request.csv_text))
    required = {"claim_id", "member_name", "member_dob", "service_date", "amount", "submitted_payer"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise HTTPException(422, f"CSV requires columns: {', '.join(sorted(required))}")
    created, duplicates, errors = [], [], []
    for row_number, row in enumerate(reader, start=2):
        if row_number > 502:
            errors.append({"row": row_number, "error": "Maximum batch size is 500 claims"})
            break
        try:
            row["amount"] = float(row["amount"])
            row["accident_related"] = str(row.get("accident_related", "false")).casefold() in {"true", "1", "yes"}
            for optional, default in {"member_id": None, "claim_type": "MEDICAL", "diagnosis_group": "GENERAL"}.items():
                row[optional] = row.get(optional) or default
            claim = ClaimInput.model_validate(row).model_dump(mode="json")
            if db.get_claim(claim["claim_id"]):
                duplicates.append(claim["claim_id"])
                continue
            db.put_claim(claim)
            db.append_audit(claim["claim_id"], "CLAIM_INGESTED", {"source": "csv", "actor": user["username"], "row": row_number})
            created.append(claim["claim_id"])
        except Exception as exc:
            errors.append({"row": row_number, "claim_id": row.get("claim_id"), "error": str(exc)[:300]})
    return {"created": created, "duplicates": duplicates, "errors": errors, "summary": {"created": len(created), "duplicates": len(duplicates), "errors": len(errors)}}


@app.post("/api/claims/upload-edi")
def upload_synthetic_edi(request: EdiUploadRequest, user: dict = Depends(require_roles("ANALYST"))) -> dict:
    try:
        parsed = parse_synthetic_837(request.edi_text)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    created, duplicates = [], []
    for model in parsed:
        claim = model.model_dump(mode="json")
        if db.get_claim(claim["claim_id"]):
            duplicates.append(claim["claim_id"])
            continue
        db.put_claim(claim)
        db.append_audit(claim["claim_id"], "CLAIM_INGESTED", {"source": "synthetic_edi", "actor": user["username"]})
        created.append(claim["claim_id"])
    return {"created": created, "duplicates": duplicates, "format": "CLAIMARMOR_EDI_LIKE_V1", "x12_certified": False}


@app.post("/api/stream/simulate")
def simulate_claim_stream(request: StreamSimulationRequest, user: dict = Depends(require_roles("ANALYST"))) -> dict:
    events = []
    for sequence, claim_id in enumerate(request.claim_ids, start=1):
        claim = db.get_claim(claim_id)
        if not claim:
            events.append({"sequence": sequence, "claim_id": claim_id, "status": "NOT_FOUND"})
            continue
        db.append_audit(claim_id, "STREAM_EVENT_RECEIVED", {"sequence": sequence, "actor": user["username"]})
        result = investigate(claim).model_dump(mode="json")
        events.append({"sequence": sequence, "claim_id": claim_id, "status": "PROCESSED", "route": result["route"], "confidence": result["confidence"]})
    return {"stream_id": str(uuid.uuid4()), "events": events, "processed": sum(event["status"] == "PROCESSED" for event in events)}


@app.get("/api/claims/{claim_id}")
def claim_detail(claim_id: str, _: dict = Depends(require_roles("ANALYST", "REVIEWER", "AUDITOR"))) -> dict:
    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    return {"claim": claim, "investigation": db.get_investigation(claim_id)}


@app.post("/api/claims/{claim_id}/investigate")
def investigate_claim(claim_id: str, user: dict = Depends(require_roles("ANALYST", "REVIEWER"))) -> dict:
    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    db.append_audit(claim_id, "INVESTIGATION_REQUESTED", {"actor": user["username"]})
    return investigate(claim).model_dump(mode="json")


@app.post("/api/claims/{claim_id}/investigate-stream")
def investigate_claim_stream(claim_id: str, user: dict = Depends(require_roles("ANALYST", "REVIEWER"))) -> StreamingResponse:
    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    db.append_audit(claim_id, "INVESTIGATION_REQUESTED", {"actor": user["username"], "mode": "stream"})

    def generate():
        try:
            for event in investigate_events(claim):
                yield json.dumps(event, default=str) + "\n"
        except Exception as exc:
            logger.exception("streamed investigation failed claim_id=%s", claim_id)
            yield json.dumps({"type": "error", "error": type(exc).__name__}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson", headers={"X-Accel-Buffering": "no", "Cache-Control": "no-store"})


@app.post("/api/claims/{claim_id}/replay")
def replay_claim(claim_id: str, user: dict = Depends(require_roles("REVIEWER", "AUDITOR"))) -> dict:
    claim = db.get_claim(claim_id)
    if not claim:
        raise HTTPException(404, "Claim not found")
    before = db.get_investigation(claim_id)
    after = investigate(claim).model_dump(mode="json")
    comparison = {"route_changed": bool(before and before["route"] != after["route"]), "confidence_delta": round(after["confidence"] - before["confidence"], 4) if before else None, "model_before": before["risk"]["model_version"] if before else None, "model_after": after["risk"]["model_version"], "evidence_before": [item["document_hash"] for item in before.get("evidence", [])] if before else [], "evidence_after": [item["document_hash"] for item in after["evidence"]]}
    db.append_audit(claim_id, "INVESTIGATION_REPLAYED", {"actor": user["username"], **comparison})
    return {"claim_id": claim_id, "before": before, "after": after, "comparison": comparison}


@app.get("/api/investigations")
def investigations(_: dict = Depends(require_roles("ANALYST", "REVIEWER", "AUDITOR"))) -> list[dict]:
    return db.list_investigations()


@app.get("/api/review-queue")
def review_queue(_: dict = Depends(require_roles("REVIEWER", "AUDITOR"))) -> list[dict]:
    reviewed = db.reviewed_claim_ids()
    return [item for item in db.list_investigations() if item["route"] in {"HOLD", "HUMAN_REVIEW", "UNDETERMINED"} and item["claim_id"] not in reviewed]


@app.post("/api/investigations/{claim_id}/review")
def review(claim_id: str, request: ReviewRequest, user: dict = Depends(require_roles("REVIEWER"))) -> dict:
    result = db.get_investigation(claim_id)
    if not result:
        raise HTTPException(404, "Investigation not found")
    review_payload = request.model_dump(mode="json")
    review_payload["reviewer"] = user["username"]
    if request.action == "REINVESTIGATE":
        claim = db.get_claim(claim_id)
        refreshed = investigate(claim).model_dump(mode="json")
        db.put_review(claim_id, review_payload)
        db.append_audit(claim_id, "REINVESTIGATION_REQUESTED", review_payload)
        return {"review": review_payload, "investigation": refreshed, "writeback": None}
    if request.action == "REQUEST_INFORMATION":
        review_payload["final_route"] = "HUMAN_REVIEW"
        db.put_review(claim_id, review_payload)
        db.append_audit(claim_id, "ADDITIONAL_INFORMATION_REQUESTED", review_payload)
        return {"review": review_payload, "writeback": None}
    final_route = request.final_route.value if request.final_route else result["route"]
    if request.action == "REJECT" and not request.final_route:
        final_route = "HUMAN_REVIEW"
    review_payload["final_route"] = final_route
    db.put_review(claim_id, review_payload)
    db.append_audit(claim_id, "HUMAN_REVIEW_COMPLETED", review_payload)
    writeback = {
        "claim_id": claim_id,
        "action": final_route,
        "recommended_primary_payer": result.get("recommended_primary_payer"),
        "review_status": request.action,
        "reviewer": user["username"],
        "destination": "SIMULATED_CORE_CLAIMS",
    }
    db.put_writeback(claim_id, writeback)
    db.append_audit(claim_id, "CLAIMS_WRITEBACK_COMPLETED", writeback)
    return {"review": review_payload, "writeback": writeback}


@app.get("/api/audit/{claim_id}")
def audit(claim_id: str, _: dict = Depends(require_roles("REVIEWER", "AUDITOR"))) -> list[dict]:
    if not db.get_claim(claim_id):
        raise HTTPException(404, "Claim not found")
    return db.get_audit(claim_id)


@app.get("/api/audit/{claim_id}/verify")
def verify_audit(claim_id: str, _: dict = Depends(require_roles("REVIEWER", "AUDITOR"))) -> dict:
    if not db.get_claim(claim_id):
        raise HTTPException(404, "Claim not found")
    return db.verify_audit_chain(claim_id)


@app.get("/api/metrics")
def metrics(_: dict = Depends(require_roles("ANALYST", "REVIEWER", "AUDITOR"))) -> dict:
    results = db.list_investigations()
    total = len(results)
    amount_at_risk = sum(item["financial_impact"]["amount_at_risk"] for item in results)
    by_route = {route: sum(1 for item in results if item["route"] == route) for route in ["CLEAR", "HOLD", "HUMAN_REVIEW", "UNDETERMINED"]}
    pending = [item for item in results if item["route"] in {"HOLD", "HUMAN_REVIEW", "UNDETERMINED"} and item["claim_id"] not in db.reviewed_claim_ids()]
    return {
        "claims_ingested": len(db.list_claims()),
        "claims_investigated": total,
        "route_counts": by_route,
        "estimated_amount_at_risk": round(amount_at_risk, 2),
        "coverage_rate": round(total / max(len(db.list_claims()), 1), 4),
        "basis": "Measured from synthetic application runs; not a real recovery estimate.",
        "model_evaluation": model_metrics(),
        "pending_reviews": len(pending),
        "storage": db.storage_info(),
    }


@app.get("/api/model/metrics")
def get_model_metrics(_: dict = Depends(require_roles("ANALYST", "REVIEWER", "AUDITOR"))) -> dict:
    result = model_metrics()
    if result is None:
        return {
            "status": "NOT_TRAINED",
            "message": "Run: python -m app.ml.train --regenerate --rows 3000",
        }
    return {"status": "READY", **result}


@app.get("/api/policies")
def policies(_: dict = Depends(require_roles("ANALYST", "REVIEWER", "AUDITOR"))) -> list[dict]:
    return get_index().records


@app.post("/api/policies", status_code=201)
def add_policy(request: PolicyIngestRequest, user: dict = Depends(require_roles("ADMIN"))) -> dict:
    text = request.content_text.strip() if request.content_text else extract_pdf_text(request.pdf_base64 or "")
    record = {
        "policy_id": request.policy_id,
        "version": request.version,
        "title": request.title,
        "section": request.section,
        "source_url": request.source_url,
        "authority": request.authority,
        "jurisdiction": request.jurisdiction,
        "effective_date": request.effective_date.isoformat(),
        "last_verified": date.today().isoformat(),
        "topics": [topic.strip()[:80] for topic in request.topics],
        "text": text,
        "status": "ACTIVE",
    }
    try:
        validate_policy_record(record)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    record["content_hash"] = hashlib.sha256(text.encode()).hexdigest()
    db.put_policy_record(record)
    get_index.cache_clear()
    db.append_audit("POLICY-CORPUS", "POLICY_VERSION_ADDED", {"policy_id": request.policy_id, "version": request.version, "actor": user["username"], "content_hash": record["content_hash"]})
    return record


@app.post("/api/policies/{policy_id}/{version}/retire")
def retire_policy(policy_id: str, version: str, user: dict = Depends(require_roles("ADMIN"))) -> dict:
    if not db.set_policy_status(policy_id, version, "RETIRED"):
        raise HTTPException(404, "Policy version not found")
    get_index.cache_clear()
    db.append_audit("POLICY-CORPUS", "POLICY_VERSION_RETIRED", {"policy_id": policy_id, "version": version, "actor": user["username"]})
    return {"policy_id": policy_id, "version": version, "status": "RETIRED"}


@app.get("/api/retrieval/metrics")
def retrieval_metrics(_: dict = Depends(require_roles("ANALYST", "REVIEWER", "AUDITOR"))) -> dict:
    return evaluate_retrieval()


@app.get("/api/evaluation")
def system_evaluation(_: dict = Depends(require_roles("ANALYST", "REVIEWER", "AUDITOR"))) -> dict:
    result = load_evaluation()
    if result is None:
        raise HTTPException(503, "Evaluation artifact not found; run python -m app.evaluation")
    return result


@app.post("/api/business/roi")
def business_roi(assumptions: RoiAssumptions, _: dict = Depends(require_roles("ANALYST", "REVIEWER", "AUDITOR"))) -> dict:
    return simulate_roi(assumptions.model_dump())


@app.get("/api/ops")
def operations(_: dict = Depends(require_roles("AUDITOR"))) -> dict:
    evaluation = load_evaluation()
    return {
        "status": "READY",
        "version": app.version,
        "storage": db.storage_info(),
        "model_ready": model_metrics() is not None,
        "evaluation_ready": evaluation is not None,
        "policy_records": len(get_index().records),
        "retrieval": evaluate_retrieval(),
        "llm_mode": os.getenv("CLAIMARMOR_LLM_MODE", "offline"),
        "data_classification": "SYNTHETIC_ONLY",
    }
