from __future__ import annotations

from datetime import date
from difflib import SequenceMatcher
from contextlib import redirect_stderr, redirect_stdout
import io
from typing import Any

import pandas as pd


def _similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, (left or "").casefold().strip(), (right or "").casefold().strip()).ratio()


def _weighted_fallback(claim: dict, members: list[dict]) -> dict:
    candidates = []
    for member in members:
        name_score = _similarity(claim["member_name"], member["name"])
        dob_score = 1.0 if str(claim["member_dob"]) == member["dob"] else 0.0
        id_score = 1.0 if claim.get("member_id") and claim["member_id"] == member["member_id"] else 0.0
        email_score = 1.0 if claim.get("member_email") and claim["member_email"] == member.get("email") else 0.0
        phone_score = 1.0 if claim.get("member_phone") and claim["member_phone"] == member.get("phone") else 0.0
        score = 0.38 * name_score + 0.30 * dob_score + 0.20 * id_score + 0.07 * email_score + 0.05 * phone_score
        available_weight = 0.68 + (0.20 if claim.get("member_id") else 0) + (0.07 if claim.get("member_email") else 0) + (0.05 if claim.get("member_phone") else 0)
        score = min(1.0, score / available_weight)
        candidates.append({"member": member, "confidence": round(score, 4)})
    candidates.sort(key=lambda item: item["confidence"], reverse=True)
    return _format_match(candidates, "weighted_fallback")


def _format_match(candidates: list[dict], method: str) -> dict:
    best = candidates[0]
    return {"member_id": best["member"]["member_id"], "member_name": best["member"]["name"], "confidence": best["confidence"], "status": "MATCHED" if best["confidence"] >= 0.85 else "REVIEW", "method": method, "candidates": candidates[:3]}


def match_member(claim: dict, members: list[dict]) -> dict:
    try:
        from splink import DuckDBAPI, Linker, SettingsCreator, block_on
        import splink.comparison_library as cl

        query = {"unique_id": "CLAIM_QUERY", "name": claim["member_name"], "dob": str(claim["member_dob"]), "email": claim.get("member_email") or "", "phone": claim.get("member_phone") or "", "address": claim.get("member_address") or "", "member_id": claim.get("member_id") or ""}
        catalogue = [{"unique_id": item["member_id"], "name": item["name"], "dob": item["dob"], "email": item.get("email", ""), "phone": item.get("phone", ""), "address": item.get("address", ""), "member_id": item["member_id"]} for item in members]
        settings = SettingsCreator(link_type="link_only", comparisons=[cl.NameComparison("name"), cl.DateOfBirthComparison("dob", input_is_string=True), cl.EmailComparison("email"), cl.ExactMatch("phone"), cl.ExactMatch("member_id")], blocking_rules_to_generate_predictions=[block_on("member_id"), block_on("dob"), block_on("email"), block_on("phone"), block_on("name")], probability_two_random_records_match=max(1 / max(len(members), 2), 0.0001))
        # Splink is intentionally combined with a conservative observable-field
        # score until a payer supplies enough labeled pairs to estimate m/u values.
        # Redirect its training notices so API/test logs remain structured.
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            linker = Linker([pd.DataFrame([query]), pd.DataFrame(catalogue)], settings, db_api=DuckDBAPI())
            predictions = linker.inference.predict(threshold_match_probability=0).as_pandas_dataframe()
        fallback = _weighted_fallback(claim, members)
        candidates = []
        for _, row in predictions.sort_values("match_probability", ascending=False).iterrows():
            other = row["unique_id_r"] if row["unique_id_l"] == "CLAIM_QUERY" else row["unique_id_l"]
            member = next(item for item in members if item["member_id"] == other)
            candidates.append({"member": member, "confidence": round(float(row["match_probability"]), 4)})
        if candidates:
            if fallback["confidence"] > candidates[0]["confidence"]:
                winner = next(item for item in members if item["member_id"] == fallback["member_id"])
                candidates.insert(0, {"member": winner, "confidence": fallback["confidence"]})
            return _format_match(candidates, "splink_fellegi_sunter")
    except Exception:
        pass
    return _weighted_fallback(claim, members)


def active_coverages(member_id: str, service_date: str | date, coverages: list[dict]) -> list[dict]:
    target = date.fromisoformat(str(service_date))
    results = []
    for coverage in coverages:
        if coverage["member_id"] != member_id:
            continue
        start = date.fromisoformat(coverage["start"])
        end = date.fromisoformat(coverage["end"]) if coverage.get("end") else date.max
        item = dict(coverage)
        item["active_on_service_date"] = start <= target <= end
        results.append(item)
    return results
