from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Callable

from fastapi import Depends, Header, HTTPException

from app import db


DEMO_USERS = {
    "analyst": ("Analyst123!", "ANALYST", "Claims Analyst"),
    "reviewer": ("Review123!", "REVIEWER", "COB Reviewer"),
    "auditor": ("Audit123!", "AUDITOR", "Audit Observer"),
    "admin": ("Admin123!", "ADMIN", "Platform Administrator"),
}


def _password_hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 180_000).hex()


def seed_users() -> None:
    for username, (password, role, display_name) in DEMO_USERS.items():
        if db.get_user(username):
            continue
        salt = hashlib.sha256(f"claimarmor-demo-{username}".encode()).hexdigest()[:32]
        db.put_user(username, _password_hash(password, salt), salt, role, display_name)


def authenticate(username: str, password: str) -> dict | None:
    user = db.get_user(username)
    if not user or not user["active"]:
        return None
    if not hmac.compare_digest(user["password_hash"], _password_hash(password, user["salt"])):
        return None
    return {"username": user["username"], "role": user["role"], "display_name": user["display_name"]}


def _secret() -> bytes:
    return os.getenv("CLAIMARMOR_AUTH_SECRET", "claimarmor-local-demo-secret").encode()


def issue_token(user: dict, lifetime_seconds: int = 28_800) -> str:
    payload = {**user, "exp": int(time.time()) + lifetime_seconds}
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")
    signature = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def decode_token(token: str) -> dict:
    try:
        body, signature = token.split(".", 1)
        expected = hmac.new(_secret(), body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("signature")
        padded = body + "=" * (-len(body) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode())
        if payload["exp"] < int(time.time()):
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(401, "Invalid or expired access token") from exc


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Authentication required")
    return decode_token(authorization[7:])


def require_roles(*roles: str) -> Callable:
    def dependency(user: dict = Depends(current_user)) -> dict:
        if user["role"] not in roles and user["role"] != "ADMIN":
            raise HTTPException(403, f"Role {user['role']} cannot perform this operation")
        return user
    return dependency

