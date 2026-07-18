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
SAFE_ID = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$"
SHA256 = r"^[0-9a-f]{64}$"


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
    ORCHESTRATION_BUNDLE = "orchestration_bundle"
    FULL_VISIBLE_EXCHANGE = "full_visible_exchange"


class ContentMessage(StrictModel):
    message_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    kind: Literal["instruction", "delegation", "input", "public_response", "output"]
    content: str
    sha256: str = Field(pattern=SHA256)
    source_label: str = Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")


class ConversationEnvelope(StrictModel):
    schema_version: Literal[2] = 2
    capture_id: str = Field(pattern=SAFE_ID)
    run_id: str = Field(pattern=SAFE_ID)
    case_key: str = Field(pattern=r"^[0-9a-f]{20}$")
    role: AgentRole
    invocation: int = Field(ge=1)
    coverage: Coverage
    status: EnvelopeStatus
    input_fingerprint: str = Field(pattern=SHA256)
    messages: list[ContentMessage]
    created_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_messages(self) -> ConversationEnvelope:
        if self.status is EnvelopeStatus.OBSERVED and not self.messages:
            raise ValueError("Observed envelopes must contain messages")
        ids = [message.message_id for message in self.messages]
        if len(ids) != len(set(ids)):
            raise ValueError("Envelope message IDs must be unique")
        return self


class EvidenceEntry(StrictModel):
    source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._/-]{0,299}$")
    repository: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]{0,127}$")
    relative_path: str = Field(min_length=1, max_length=500)
    sha256: str = Field(pattern=SHA256)
    size: int = Field(ge=0)
    truncated: bool = False


class FrozenCaseManifest(StrictModel):
    schema_version: Literal[2] = 2
    case_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    capture_id: str = Field(pattern=SAFE_ID)
    run_id: str = Field(pattern=SAFE_ID)
    subject_provider: Literal["agy", "claude", "codex"]
    subject_model: str | None
    envelope_count: int = Field(ge=1)
    evidence_entries: list[EvidenceEntry]
    omissions: list[str]
    files: dict[str, str]
    content_digest: str = Field(pattern=SHA256)
    created_at: str


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

    @model_validator(mode="after")
    def supported_has_citation(self) -> ClaimAssessment:
        if self.status == "supported" and not self.message_ids:
            raise ValueError("Supported claims require at least one message citation")
        return self


class VerificationRequest(StrictModel):
    claim_id: str = Field(pattern=r"^claim-[0-9]+$")
    source_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._/-]{0,299}$")
    query: str = Field(min_length=3, max_length=500)


class EvaluationResult(StrictModel):
    schema_version: Literal[2] = 2
    item_id: str = Field(pattern=SAFE_ID)
    repetition: int = Field(ge=1, le=3)
    instruction_design: AssessmentPanel
    execution_and_output: AssessmentPanel
    global_index_100: float = Field(ge=0, le=100)
    claims: list[ClaimAssessment]
    verification_requests: list[VerificationRequest] = Field(max_length=5)
    strengths: list[str]
    risks: list[str]
    confidence: float = Field(ge=0, le=1)
    profile_sha256: str = Field(pattern=SHA256)
    rubric_sha256: str = Field(pattern=SHA256)
    envelope_sha256: str = Field(pattern=SHA256)

    @model_validator(mode="after")
    def validate_result(self) -> EvaluationResult:
        expected = (self.instruction_design.index_100 + self.execution_and_output.index_100) / 2
        if abs(expected - self.global_index_100) > 0.01:
            raise ValueError("Global index must be the 50/50 panel average")
        claim_ids = {claim.claim_id for claim in self.claims}
        if any(request.claim_id not in claim_ids for request in self.verification_requests):
            raise ValueError("Verification request references an unknown claim")
        return self


class BenchmarkSpec(StrictModel):
    schema_version: Literal[2, 3] = 3
    benchmark_id: str = Field(pattern=SAFE_ID)
    capture_id: str = Field(pattern=SAFE_ID)
    case_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    case_digest: str = Field(pattern=SHA256)
    subject_provider: Literal["agy", "claude", "codex"]
    subject_model: str | None
    baseline_provider: Literal["claude", "codex"] | None = None
    baseline_model: str | None = None
    judge_provider: Literal["claude", "codex"]
    judge_model: str
    rubric_sha256: str = Field(pattern=SHA256)
    profile_sha256: dict[str, str]
    repetitions: Literal[3] = 3
    plan_digest: str = Field(pattern=SHA256)
    created_at: str

    @model_validator(mode="after")
    def resolve_legacy_baseline(self) -> BenchmarkSpec:
        if self.schema_version == 2 and self.baseline_provider is None:
            if self.subject_provider not in {"claude", "codex"} or self.subject_model is None:
                raise ValueError("Legacy benchmark has no usable baseline provider")
            self.baseline_provider = "claude" if self.subject_provider == "claude" else "codex"
            self.baseline_model = self.subject_model
        if self.baseline_provider is None or self.baseline_model is None:
            raise ValueError("Benchmark baseline provider and model are required")
        return self


class PairwiseResult(StrictModel):
    schema_version: Literal[2] = 2
    repetition: int = Field(ge=1, le=3)
    blind_order: Literal["pipeline_a", "baseline_a"]
    preference: Literal["a", "b", "tie"]
    pipeline_preferred: bool | None
    rationale: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)


class HumanLabel(StrictModel):
    schema_version: Literal[2] = 2
    benchmark_id: str = Field(pattern=SAFE_ID)
    blind_item_id: str = Field(pattern=SAFE_ID)
    rater_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
    instruction_scores: dict[str, int] | None = None
    execution_scores: dict[str, int] | None = None
    pairwise_preference: Literal["a", "b", "tie"] | None = None
    claim_support: dict[str, Literal["supported", "unsupported", "unclear"]] | None = None
    created_at: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_scores(self) -> HumanLabel:
        if (self.instruction_scores is None) != (self.execution_scores is None):
            raise ValueError("Human panel scores must be supplied together")
        if not any((self.instruction_scores, self.pairwise_preference, self.claim_support)):
            raise ValueError("A label must contain panel scores, pairwise preference, or claims")
        for scores in (self.instruction_scores, self.execution_scores):
            if scores is None:
                continue
            if set(scores) != set(DIMENSIONS) or any(
                not 0 <= score <= 4 for score in scores.values()
            ):
                raise ValueError("Human scores must cover every dimension from 0 through 4")
        return self
