from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DIMENSIONS = (
    "clarity",
    "role_alignment",
    "relevance_and_focus",
    "internal_consistency",
    "grounding_and_evidence_discipline",
    "completeness_and_coverage",
    "usefulness_and_actionability",
    "uncertainty_calibration",
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class AgentRole(StrEnum):
    VERA = "vera"
    HARVEY = "harvey"
    SHADOW = "shadow"
    KAREN = "karen"
    BILL = "bill"
    DONNA = "donna"
    BASELINE = "baseline"


class EnvelopeStatus(StrEnum):
    OBSERVED = "observed"
    NOT_OBSERVED = "not_observed"
    FAILED = "failed"
    INCOMPLETE = "incomplete"


class Coverage(StrEnum):
    PROMPT_OUTPUT_ONLY = "prompt_output_only"
    DELEGATION_RESPONSE = "delegation_response"
    FULL_VISIBLE_EXCHANGE = "full_visible_exchange"


class ContentMessage(StrictModel):
    message_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    kind: Literal["instruction", "delegation", "input", "public_response", "output"]
    content: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_label: str = Field(min_length=1, max_length=200)


class ConversationEnvelope(StrictModel):
    schema_version: Literal[1] = 1
    capture_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
    run_id: str = Field(min_length=1)
    case_id: str
    role: AgentRole
    invocation: int = Field(ge=1)
    coverage: Coverage
    status: EnvelopeStatus
    input_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    messages: list[ContentMessage]
    created_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def observed_has_content(self) -> ConversationEnvelope:
        if self.status is EnvelopeStatus.OBSERVED and not self.messages:
            raise ValueError("Observed envelopes must contain messages")
        ids = [message.message_id for message in self.messages]
        if len(ids) != len(set(ids)):
            raise ValueError("Envelope message IDs must be unique")
        return self


class ProfileDimension(StrictModel):
    design_anchor: str = Field(min_length=1)
    execution_anchor: str = Field(min_length=1)


class AgentProfile(StrictModel):
    schema_version: Literal[1] = 1
    role: AgentRole
    version: str = Field(pattern=r"^[0-9]+\.[0-9]+\.[0-9]+$")
    description: str = Field(min_length=20)
    dimensions: dict[str, ProfileDimension]
    verification_source_labels: list[str]

    @model_validator(mode="after")
    def dimensions_are_exact(self) -> AgentProfile:
        if set(self.dimensions) != set(DIMENSIONS):
            raise ValueError("Profile must define exactly the common dimensions")
        return self


class DimensionAssessment(StrictModel):
    score: int = Field(ge=0, le=4)
    rationale: str = Field(min_length=1, max_length=1200)
    message_ids: list[str]


class AssessmentPanel(StrictModel):
    dimensions: dict[str, DimensionAssessment]
    index_100: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def dimensions_are_exact(self) -> AssessmentPanel:
        if set(self.dimensions) != set(DIMENSIONS):
            raise ValueError("Assessment must define exactly the common dimensions")
        expected = sum(value.score for value in self.dimensions.values()) / 32 * 100
        if abs(expected - self.index_100) > 0.01:
            raise ValueError("Panel index does not match its dimension scores")
        return self


class ClaimAssessment(StrictModel):
    claim_id: str = Field(pattern=r"^claim-[0-9]+$")
    text: str = Field(min_length=1)
    message_ids: list[str]
    status: Literal["supported", "unsupported", "unclear", "not_checked"]
    severity: Literal["low", "medium", "high"]


class VerificationRequest(StrictModel):
    claim_id: str = Field(pattern=r"^claim-[0-9]+$")
    source_label: str = Field(min_length=1, max_length=200)
    query: str = Field(min_length=1, max_length=500)


class EvaluationResult(StrictModel):
    schema_version: Literal[1] = 1
    item_id: str = Field(min_length=1)
    repetition: int = Field(ge=1, le=3)
    instruction_design: AssessmentPanel
    execution_and_output: AssessmentPanel
    global_index_100: float = Field(ge=0, le=100)
    claims: list[ClaimAssessment]
    verification_requests: list[VerificationRequest] = Field(max_length=5)
    strengths: list[str]
    risks: list[str]
    confidence: float = Field(ge=0, le=1)
    profile_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    rubric_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    envelope_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_result(self) -> EvaluationResult:
        expected = (self.instruction_design.index_100 + self.execution_and_output.index_100) / 2
        if abs(expected - self.global_index_100) > 0.01:
            raise ValueError("Global index must be the 50/50 panel average")
        message_claims = {claim.claim_id for claim in self.claims}
        if any(request.claim_id not in message_claims for request in self.verification_requests):
            raise ValueError("Verification request references an unknown claim")
        return self


class HumanLabel(StrictModel):
    schema_version: Literal[1] = 1
    benchmark_id: str = Field(min_length=1)
    blind_item_id: str = Field(min_length=1)
    rater_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
    instruction_scores: dict[str, int] | None = None
    execution_scores: dict[str, int] | None = None
    pairwise_preference: Literal["a", "b", "tie"] | None = None
    created_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scores(self) -> HumanLabel:
        if (self.instruction_scores is None) != (self.execution_scores is None):
            raise ValueError("Human panel scores must be supplied together")
        if self.instruction_scores is None and self.pairwise_preference is None:
            raise ValueError("A human label must contain panel scores or a pairwise preference")
        for scores in (self.instruction_scores, self.execution_scores):
            if scores is None:
                continue
            if set(scores) != set(DIMENSIONS):
                raise ValueError("Human labels must score every common dimension")
            if any(score < 0 or score > 4 for score in scores.values()):
                raise ValueError("Human scores must be between 0 and 4")
        return self
