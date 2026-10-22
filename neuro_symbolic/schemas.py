"""Typed request and orchestration schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GuidedObservations(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lesion_present: bool | None = None
    lesion_shape: str | None = None
    lesion_color: str | None = None
    necrosis_present: bool | None = None
    lesion_center_color: str | None = None
    lesion_margin_color: str | None = None
    lesion_size: str | None = None
    lesion_width_mm: float | None = None
    lesion_distribution: str | None = None
    leaf_region: str | None = None
    halo_present: bool | None = None
    halo_color: str | None = None
    zonation_present: bool | None = None
    blighting: bool | str | None = None
    dryness: bool | str | None = None
    coalescence: bool | None = None
    yellowing: bool | str | None = None
    visual_status: str | None = None
    vigor: str | None = None
    leaf_age: str | None = None
    growth_stage: str | None = None
    other_observations: list[str] = Field(default_factory=list, max_length=20)


class CNNOutput(BaseModel):
    sample_id: str
    predicted_class: str
    confidence: float = Field(ge=0, le=1)
    second_class: str
    second_confidence: float = Field(ge=0, le=1)
    class_probabilities: dict[str, float]


class ObservationResult(BaseModel):
    input_mode: str
    provided_observations: dict[str, Any]
    normalized_observations: dict[str, Any]
    observation_sources: dict[str, str]
    missing_required_or_relevant_features: list[str]
    categorical_vocabulary_status: str


class EvidenceRecord(BaseModel):
    rule_id: str
    runtime_state: str
    evidence_ids: list[str] = Field(default_factory=list)
    source_document_id: str | None = None
    citation: str | None = None
    source_rule_record: dict[str, Any]


class SymbolicResult(BaseModel):
    status: str
    prediction: str | None
    score: float
    reliability: float
    confidence_category: str
    disease_scores: dict[str, float]
    matched_rule_ids: list[str]
    matched_rules: list[dict[str, Any]]
    matched_evidence_ids: list[str]
    reasoning_trace: list[dict[str, Any]]
    limitations: list[str]


class FusionResult(BaseModel):
    final_prediction: str | None
    display_name: str
    candidate_prediction: str
    candidate_display_name: str
    final_confidence: float
    cnn_weight: float
    symbolic_weight: float
    raw_phase7_cnn_weight: float
    raw_phase7_symbolic_weight: float
    abstention_policy_applied: bool
    class_scores: dict[str, float]
    agreement_status: str
    conflict_status: str
    resolution: str


class DiagnosticConflictResult(BaseModel):
    status: str
    final_prediction: str | None
    candidate_prediction: str
    final_confidence: float
    conflict_detected: bool
    symbolic_abstained: bool
    requires_manual_review: bool
    resolution: str


class ManagementResult(BaseModel):
    selected_rule: dict[str, Any] | None
    recommendation: str
    warning: str
    actionable: bool
    advisory_only: bool
    validation_status: str
    runtime_state: str
    sources: list[Any]


class ExplanationResult(BaseModel):
    summary: str
    provided_observed_features: list[dict[str, Any]]
    matched_observed_features: list[str]
    matched_rule_ids: list[str]
    evidence_ids: list[str]
    citations: list[str]
    why_cnn_contributed: str
    why_symbolic_contributed: str
    why_final_prediction_was_selected: str
    reasoning_trace: list[dict[str, Any]]
    limitations: list[str]
