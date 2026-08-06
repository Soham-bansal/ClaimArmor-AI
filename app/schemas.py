from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class DecisionRoute(str, Enum):
    CLEAR = "CLEAR"
    HOLD = "HOLD"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    UNDETERMINED = "UNDETERMINED"


class ClaimInput(BaseModel):
    claim_id: str = Field(min_length=3, max_length=80)
    member_name: str = Field(min_length=2, max_length=120)
    member_dob: date
    member_id: str | None = None
    member_email: str | None = None
    member_phone: str | None = None
    member_address: str | None = None
    service_date: date
    amount: float = Field(gt=0, le=10_000_000)
    submitted_payer: str = Field(min_length=2, max_length=80)
    claim_type: str = "MEDICAL"
    accident_related: bool = False
    diagnosis_group: str = "GENERAL"
    provider_id: str | None = None
    employer_id: str | None = None
    employment_active: bool | None = None
    employer_size: int | None = Field(default=None, ge=0, le=1_000_000)
    disability: bool = False
    relationship: str = "SELF"

    @field_validator("claim_id", "member_name", "submitted_payer", "claim_type")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class ReviewRequest(BaseModel):
    reviewer: str = Field(min_length=2, max_length=80)
    action: str
    reason: str = Field(min_length=3, max_length=500)
    final_route: DecisionRoute | None = None

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        value = value.upper().strip()
        if value not in {"APPROVE", "REJECT", "OVERRIDE", "REQUEST_INFORMATION", "REINVESTIGATE"}:
            raise ValueError("unsupported review action")
        return value


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=200)


class CsvUploadRequest(BaseModel):
    csv_text: str = Field(min_length=10, max_length=2_000_000)


class RoiAssumptions(BaseModel):
    annual_claims: int = Field(default=100_000, ge=1, le=1_000_000_000)
    average_claim_amount: float = Field(default=2500, gt=0, le=10_000_000)
    leakage_rate: float = Field(default=0.025, ge=0, le=1)
    value_detection_rate: float = Field(default=0.837, ge=0, le=1)
    review_rate: float = Field(default=0.25, ge=0, le=1)
    review_cost: float = Field(default=35, ge=0, le=100_000)
    false_positive_rate: float = Field(default=0.08, ge=0, le=1)
    false_positive_cost: float = Field(default=75, ge=0, le=100_000)
    annual_platform_cost: float = Field(default=750_000, gt=0, le=1_000_000_000)


class EdiUploadRequest(BaseModel):
    edi_text: str = Field(min_length=20, max_length=2_000_000)


class StreamSimulationRequest(BaseModel):
    claim_ids: list[str] = Field(min_length=1, max_length=100)


class PolicyIngestRequest(BaseModel):
    policy_id: str = Field(pattern=r"^[A-Z0-9_-]{3,80}$")
    version: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=3, max_length=200)
    section: str = Field(min_length=1, max_length=200)
    source_url: str = Field(pattern=r"^https://")
    authority: str = Field(min_length=2, max_length=160)
    jurisdiction: str = Field(min_length=2, max_length=120)
    effective_date: date
    topics: list[str] = Field(min_length=1, max_length=30)
    content_text: str | None = Field(default=None, max_length=1_000_000)
    pdf_base64: str | None = Field(default=None, max_length=8_000_000)

    @model_validator(mode="after")
    def require_one_content_source(self):
        if bool(self.content_text) == bool(self.pdf_base64):
            raise ValueError("Provide exactly one of content_text or pdf_base64")
        return self


class InvestigationResult(BaseModel):
    claim_id: str
    member_match: dict[str, Any]
    coverage_timeline: list[dict[str, Any]]
    risk: dict[str, Any]
    rules: list[dict[str, Any]]
    evidence: list[dict[str, Any]]
    agent_trace: list[dict[str, Any]]
    recommended_primary_payer: str | None
    route: DecisionRoute
    confidence: float
    financial_impact: dict[str, Any]
    explanation: str
    limitations: list[str]
