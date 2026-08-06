from __future__ import annotations

import hashlib
import base64
import io
import json
import re
from functools import lru_cache
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


POLICY_PATH = Path("data/policies/cms_msp_chunks.json")
TRUSTED_PREFIXES = (
    "https://www.cms.gov/",
    "https://cms.gov/",
    "https://www.ecfr.gov/",
    "https://www.medicare.gov/",
)
INJECTION_MARKERS = ("ignore previous instructions", "system prompt", "developer message", "reveal secrets", "override safeguards")
DOMAIN_EXPANSIONS = {
    "auto": "accident liability no-fault",
    "car": "accident auto liability no-fault",
    "job": "current employment employer group health plan",
    "working": "current employment employer group health plan",
    "large employer": "20 employees 100 employees employer primary",
    "small employer": "under 20 employees medicare primary",
}


def _hash(record: dict) -> str:
    stable = json.dumps({key: record[key] for key in ("policy_id", "title", "section", "source_url", "text")}, sort_keys=True)
    return hashlib.sha256(stable.encode()).hexdigest()


def validate_policy_record(record: dict) -> None:
    if not record["source_url"].startswith(TRUSTED_PREFIXES):
        raise ValueError(f"Untrusted policy source: {record['source_url']}")
    lowered = record["text"].casefold()
    if any(marker in lowered for marker in INJECTION_MARKERS):
        raise ValueError(f"Potential prompt injection in policy record: {record['policy_id']}")


def extract_pdf_text(encoded_pdf: str) -> str:
    try:
        from pypdf import PdfReader

        raw = base64.b64decode(encoded_pdf, validate=True)
        if not raw.startswith(b"%PDF"):
            raise ValueError("Uploaded content is not a PDF")
        reader = PdfReader(io.BytesIO(raw))
        if len(reader.pages) > 250:
            raise ValueError("PDF exceeds the 250-page demo limit")
        text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
        if len(text) < 20:
            raise ValueError("PDF contains no extractable text")
        return text[:1_000_000]
    except (ValueError, TypeError) as exc:
        raise ValueError(str(exc)) from exc
    except Exception as exc:
        raise ValueError("Unable to parse PDF safely") from exc


class PolicyIndex:
    def __init__(self, path: Path = POLICY_PATH):
        records = json.loads(path.read_text(encoding="utf-8"))
        try:
            from app import db

            records.extend(db.list_policy_records(active_only=True))
        except Exception:
            # The static corpus remains available during initial database setup.
            pass
        for record in records:
            validate_policy_record(record)
            record["document_hash"] = _hash(record)
        self.records = records
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)
        corpus = [f"{' '.join(item['topics'])} {item['title']} {item['section']} {item['text']}" for item in records]
        self.matrix = self.vectorizer.fit_transform(corpus)

    def search(self, query: str, limit: int = 4) -> list[dict]:
        expanded = query
        lowered = query.casefold()
        for phrase, expansion in DOMAIN_EXPANSIONS.items():
            if phrase in lowered:
                expanded += f" {expansion}"
        scores = cosine_similarity(self.vectorizer.transform([expanded]), self.matrix)[0]
        order = scores.argsort()[::-1]
        results = []
        for index in order[:limit]:
            if scores[index] <= 0:
                continue
            results.append({**self.records[int(index)], "retrieval_score": round(float(scores[index]), 4)})
        return results


@lru_cache(maxsize=1)
def get_index() -> PolicyIndex:
    return PolicyIndex()


def retrieve_evidence(query: str, limit: int = 4) -> list[dict]:
    safe_query = re.sub(r"[^a-zA-Z0-9 _-]", " ", query)[:1500]
    return get_index().search(safe_query, limit)


def evaluate_retrieval() -> dict:
    cases = [
        ("car accident with active auto coverage", "CMS-MSP-LIABILITY-001"),
        ("working aged small employer under 20", "CMS-MSP-WORKING-AGED-SMALL"),
        ("working aged employer has 20 employees", "CMS-MSP-WORKING-AGED-LARGE"),
        ("provider needs to ask about other insurance", "CMS-PROVIDER-INQUIRY-001"),
        ("recover mistaken Medicare primary payment", "CMS-COB-RECOVERY-001"),
    ]
    reciprocal_ranks = []
    hits = 0
    details = []
    for query, expected in cases:
        ids = [item["policy_id"] for item in retrieve_evidence(query, limit=4)]
        rank = ids.index(expected) + 1 if expected in ids else None
        hits += int(rank is not None)
        reciprocal_ranks.append(1 / rank if rank else 0)
        details.append({"query": query, "expected": expected, "rank": rank, "retrieved": ids})
    return {"cases": len(cases), "hit_at_4": round(hits / len(cases), 4), "mrr": round(sum(reciprocal_ranks) / len(cases), 4), "details": details}
