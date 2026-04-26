from typing import Literal
from pydantic import BaseModel, Field, field_validator
from safety import check_strings


class HealthResponse(BaseModel):
    status: str = "ok"


class CreateSessionRequest(BaseModel):
    consult_type: str


class CreateSessionResponse(BaseModel):
    session_id: str
    status: str


class DemoTranscriptRequest(BaseModel):
    text: str


class SuggestionOut(BaseModel):
    question: str
    reason: str
    priority: Literal["red", "yellow", "green"]
    status: str
    answer_found: str | None = None
    related_diagnoses: list[str] = Field(default_factory=list)


class DifferentialOut(BaseModel):
    diagnosis: str
    rank: int
    confidence: float
    supporting_evidence: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)


class WorkerOutput(BaseModel):
    suggestions: list[SuggestionOut]
    differentials: list[DifferentialOut]
    summary: str
    safety_note: str

    @field_validator("summary", "safety_note")
    @classmethod
    def _safe_text(cls, v: str) -> str:
        check_strings([v])
        return v

    @field_validator("suggestions")
    @classmethod
    def _validate_suggestions(cls, vals: list[SuggestionOut]) -> list[SuggestionOut]:
        check_strings([f"{x.question} {x.reason} {x.answer_found or ''}" for x in vals])
        return vals

    @field_validator("differentials")
    @classmethod
    def _validate_diff(cls, vals: list[DifferentialOut]) -> list[DifferentialOut]:
        check_strings([
            " ".join([d.diagnosis] + d.supporting_evidence + d.missing_information + d.suggested_questions)
            for d in vals
        ])
        return vals


class SessionStateResponse(BaseModel):
    session_id: str
    consult_type: str
    status: str
    transcript: str
    suggestions: list[SuggestionOut]
    differentials: list[DifferentialOut]
    analysis_status: str
    safety_note: str
