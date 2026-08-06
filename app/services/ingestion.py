from __future__ import annotations

from app.schemas import ClaimInput


def parse_synthetic_837(text: str) -> list[ClaimInput]:
    """Parse the documented ClaimArmor EDI-like CLM segment, not licensed X12."""
    claims = []
    for number, segment in enumerate(text.replace("\n", "").split("~"), start=1):
        segment = segment.strip()
        if not segment:
            continue
        elements = segment.split("*")
        if elements[0] != "CLM" or len(elements) < 9:
            raise ValueError(f"Segment {number} must be CLM*id*member_id*name*dob*service_date*amount*payer*accident")
        claims.append(ClaimInput(
            claim_id=elements[1], member_id=elements[2] or None, member_name=elements[3], member_dob=elements[4],
            service_date=elements[5], amount=float(elements[6]), submitted_payer=elements[7],
            accident_related=elements[8].casefold() in {"1", "true", "yes"},
            claim_type="TRAUMA" if elements[8].casefold() in {"1", "true", "yes"} else "MEDICAL",
            diagnosis_group="ACCIDENT" if elements[8].casefold() in {"1", "true", "yes"} else "GENERAL",
        ))
    if not claims:
        raise ValueError("No CLM segments found")
    return claims


def encode_synthetic_837(claim: dict) -> str:
    return "*".join(["CLM", claim["claim_id"], claim.get("member_id") or "", claim["member_name"], str(claim["member_dob"]), str(claim["service_date"]), str(claim["amount"]), claim["submitted_payer"], "1" if claim.get("accident_related") else "0"]) + "~"
