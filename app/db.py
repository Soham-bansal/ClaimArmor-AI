from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import Column, Integer, MetaData, String, Table, Text, create_engine, delete, func, insert, select


DB_PATH = Path(os.getenv("CLAIMARMOR_DB", "claimarmor.db"))
metadata = MetaData()

claims_table = Table("claims", metadata, Column("claim_id", String(80), primary_key=True), Column("payload", Text, nullable=False), Column("created_at", String(40), nullable=False))
investigations_table = Table("investigations", metadata, Column("claim_id", String(80), primary_key=True), Column("result", Text, nullable=False), Column("updated_at", String(40), nullable=False))
reviews_table = Table("reviews", metadata, Column("id", Integer, primary_key=True, autoincrement=True), Column("claim_id", String(80), nullable=False, index=True), Column("payload", Text, nullable=False), Column("created_at", String(40), nullable=False))
writebacks_table = Table("writebacks", metadata, Column("claim_id", String(80), primary_key=True), Column("payload", Text, nullable=False), Column("created_at", String(40), nullable=False))
audit_table = Table("audit_events", metadata, Column("id", Integer, primary_key=True, autoincrement=True), Column("claim_id", String(80), nullable=False, index=True), Column("event_type", String(80), nullable=False), Column("payload", Text, nullable=False), Column("previous_hash", String(64), nullable=False), Column("event_hash", String(64), nullable=False), Column("created_at", String(40), nullable=False))
users_table = Table("users", metadata, Column("username", String(80), primary_key=True), Column("password_hash", String(256), nullable=False), Column("salt", String(64), nullable=False), Column("role", String(40), nullable=False), Column("display_name", String(120), nullable=False), Column("active", Integer, nullable=False, default=1))
policies_table = Table("policies", metadata, Column("record_key", String(130), primary_key=True), Column("policy_id", String(80), nullable=False, index=True), Column("version", String(40), nullable=False), Column("status", String(20), nullable=False), Column("payload", Text, nullable=False), Column("created_at", String(40), nullable=False))


def database_url() -> str:
    configured = os.getenv("CLAIMARMOR_DATABASE_URL", "").strip()
    return configured or f"sqlite:///{DB_PATH.as_posix()}"


def _engine():
    url = database_url()
    return create_engine(url, future=True, connect_args={"check_same_thread": False} if url.startswith("sqlite") else {})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    engine = _engine()
    try:
        metadata.create_all(engine)
    finally:
        engine.dispose()


def storage_info() -> dict:
    url = database_url()
    return {"backend": "postgresql" if url.startswith("postgresql") else "sqlite", "configured": bool(os.getenv("CLAIMARMOR_DATABASE_URL"))}


def _put_unique(table: Table, key_column, key: str, values: dict) -> None:
    engine = _engine()
    try:
        with engine.begin() as conn:
            conn.execute(delete(table).where(key_column == key))
            conn.execute(insert(table).values(**values))
    finally:
        engine.dispose()


def put_claim(claim: dict[str, Any]) -> None:
    _put_unique(claims_table, claims_table.c.claim_id, claim["claim_id"], {"claim_id": claim["claim_id"], "payload": json.dumps(claim, sort_keys=True, default=str), "created_at": _now()})


def list_claims() -> list[dict[str, Any]]:
    engine = _engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(select(claims_table.c.payload).order_by(claims_table.c.created_at)).all()
        return [json.loads(row.payload) for row in rows]
    finally:
        engine.dispose()


def get_claim(claim_id: str) -> dict[str, Any] | None:
    engine = _engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(select(claims_table.c.payload).where(claims_table.c.claim_id == claim_id)).first()
        return json.loads(row.payload) if row else None
    finally:
        engine.dispose()


def put_investigation(claim_id: str, result: dict[str, Any]) -> None:
    _put_unique(investigations_table, investigations_table.c.claim_id, claim_id, {"claim_id": claim_id, "result": json.dumps(result, sort_keys=True, default=str), "updated_at": _now()})


def get_investigation(claim_id: str) -> dict[str, Any] | None:
    engine = _engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(select(investigations_table.c.result).where(investigations_table.c.claim_id == claim_id)).first()
        return json.loads(row.result) if row else None
    finally:
        engine.dispose()


def list_investigations() -> list[dict[str, Any]]:
    engine = _engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(select(investigations_table.c.result).order_by(investigations_table.c.updated_at.desc())).all()
        return [json.loads(row.result) for row in rows]
    finally:
        engine.dispose()


def put_review(claim_id: str, payload: dict[str, Any]) -> None:
    engine = _engine()
    try:
        with engine.begin() as conn:
            conn.execute(insert(reviews_table).values(claim_id=claim_id, payload=json.dumps(payload, sort_keys=True, default=str), created_at=_now()))
    finally:
        engine.dispose()


def reviewed_claim_ids() -> set[str]:
    engine = _engine()
    try:
        with engine.connect() as conn:
            return set(conn.execute(select(reviews_table.c.claim_id).distinct()).scalars().all())
    finally:
        engine.dispose()


def put_writeback(claim_id: str, payload: dict[str, Any]) -> None:
    _put_unique(writebacks_table, writebacks_table.c.claim_id, claim_id, {"claim_id": claim_id, "payload": json.dumps(payload, sort_keys=True, default=str), "created_at": _now()})


def append_audit(claim_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload, sort_keys=True, default=str)
    created_at = _now()
    engine = _engine()
    try:
        with engine.begin() as conn:
            previous_hash = conn.execute(select(audit_table.c.event_hash).where(audit_table.c.claim_id == claim_id).order_by(audit_table.c.id.desc()).limit(1)).scalar_one_or_none() or "GENESIS"
            event_hash = hashlib.sha256(f"{claim_id}|{event_type}|{encoded}|{previous_hash}|{created_at}".encode()).hexdigest()
            conn.execute(insert(audit_table).values(claim_id=claim_id, event_type=event_type, payload=encoded, previous_hash=previous_hash, event_hash=event_hash, created_at=created_at))
        return {"event_type": event_type, "event_hash": event_hash, "previous_hash": previous_hash, "created_at": created_at}
    finally:
        engine.dispose()


def get_audit(claim_id: str) -> list[dict[str, Any]]:
    engine = _engine()
    try:
        with engine.connect() as conn:
            rows = conn.execute(select(audit_table).where(audit_table.c.claim_id == claim_id).order_by(audit_table.c.id)).mappings().all()
        return [{**dict(row), "payload": json.loads(row["payload"])} for row in rows]
    finally:
        engine.dispose()


def verify_audit_chain(claim_id: str) -> dict:
    events = get_audit(claim_id)
    expected_previous = "GENESIS"
    failures = []
    for event in events:
        encoded = json.dumps(event["payload"], sort_keys=True, default=str)
        expected_hash = hashlib.sha256(
            f"{claim_id}|{event['event_type']}|{encoded}|{expected_previous}|{event['created_at']}".encode()
        ).hexdigest()
        if event["previous_hash"] != expected_previous:
            failures.append({"event_id": event["id"], "reason": "previous_hash_mismatch"})
        if event["event_hash"] != expected_hash:
            failures.append({"event_id": event["id"], "reason": "event_hash_mismatch"})
        expected_previous = event["event_hash"]
    return {"claim_id": claim_id, "valid": not failures, "events_checked": len(events), "failures": failures, "head_hash": expected_previous}


def put_user(username: str, password_hash: str, salt: str, role: str, display_name: str) -> None:
    _put_unique(users_table, users_table.c.username, username, {"username": username, "password_hash": password_hash, "salt": salt, "role": role, "display_name": display_name, "active": 1})


def get_user(username: str) -> dict | None:
    engine = _engine()
    try:
        with engine.connect() as conn:
            row = conn.execute(select(users_table).where(users_table.c.username == username)).mappings().first()
        return dict(row) if row else None
    finally:
        engine.dispose()


def put_policy_record(record: dict[str, Any]) -> None:
    key = f"{record['policy_id']}:{record['version']}"
    _put_unique(policies_table, policies_table.c.record_key, key, {"record_key": key, "policy_id": record["policy_id"], "version": record["version"], "status": record.get("status", "ACTIVE"), "payload": json.dumps(record, sort_keys=True, default=str), "created_at": _now()})


def list_policy_records(active_only: bool = False) -> list[dict[str, Any]]:
    engine = _engine()
    try:
        with engine.connect() as conn:
            query = select(policies_table)
            if active_only:
                query = query.where(policies_table.c.status == "ACTIVE")
            rows = conn.execute(query.order_by(policies_table.c.created_at)).mappings().all()
        return [{**json.loads(row["payload"]), "status": row["status"]} for row in rows]
    finally:
        engine.dispose()


def set_policy_status(policy_id: str, version: str, status: str) -> bool:
    engine = _engine()
    try:
        with engine.begin() as conn:
            row = conn.execute(select(policies_table).where(policies_table.c.policy_id == policy_id, policies_table.c.version == version)).mappings().first()
            if not row:
                return False
            payload = json.loads(row["payload"])
            payload["status"] = status
            conn.execute(policies_table.update().where(policies_table.c.record_key == row["record_key"]).values(status=status, payload=json.dumps(payload, sort_keys=True, default=str)))
        return True
    finally:
        engine.dispose()
