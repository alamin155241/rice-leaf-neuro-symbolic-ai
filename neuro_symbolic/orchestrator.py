"""Single orchestration path for safety, Phase 6, Phase 7, and explanation."""

from __future__ import annotations

import os
from copy import deepcopy
from typing import Any
from uuid import uuid4

from conflict_resolution.conflict_resolver import resolve_management_rules

from .artifact_loader import artifact_info, get_runtime_mode
from .class_mapping import (
    CNN_CLASS_ORDER,
    canonical_probabilities_to_research,
    display_name,
    research_probabilities_to_canonical,
    to_canonical_key,
)
from .diagnostic_conflict_resolver import resolve_diagnostic_conflict
from .explainability import GRADCAM_DISCLAIMER, build_explanation
from .fusion_engine import fuse_predictions
from .fusion_engine import normalize_probability_dict, top_two
from .observation import GuidedObservationPolicyError, prepare_observations
from .reasoning_engine import reasoning_engine
from .safety_layer import evaluate_safety
from .schemas import CNNOutput, GuidedObservations


def _environment_flag_enabled(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _apply_runtime_fusion_policy(
    phase7_result: dict[str, Any],
    symbolic_result: dict[str, Any],
    cnn_probabilities: dict[str, float],
) -> tuple[dict[str, Any], bool]:
    """Apply runtime abstention semantics outside the immutable Phase 7 core."""
    effective = deepcopy(phase7_result)
    abstained = (
        symbolic_result.get("status") == "insufficient_observation_evidence"
    )
    if not abstained:
        return effective, False

    normalized_cnn = normalize_probability_dict(
        canonical_probabilities_to_research(cnn_probabilities)
    )
    (final_class, final_score), (second_class, second_score) = top_two(normalized_cnn)
    effective["fusion"].update(
        {
            "cnn_weight": 1.0,
            "symbolic_weight": 0.0,
            "weight_reason": (
                "Symbolic reasoning abstained; effective runtime fusion uses "
                "CNN evidence only."
            ),
            "class_scores": {
                key: round(value, 4) for key, value in normalized_cnn.items()
            },
            "final_prediction": final_class,
            "final_confidence": round(final_score, 4),
            "second_choice": second_class,
            "second_choice_score": round(second_score, 4),
            "final_margin": round(final_score - second_score, 4),
            "decision_status": "SYMBOLIC_ABSTENTION",
        }
    )
    effective["conflict"].update(
        {
            "detected": False,
            "resolution": (
                "Symbolic reasoning abstained; no symbolic evidence contributed "
                "to the effective runtime result."
            ),
        }
    )
    return effective, True


def orchestrate_diagnosis(
    *,
    cnn_probabilities: dict[str, float],
    top_label: str,
    top_confidence: float,
    second_label: str,
    second_confidence: float,
    attention_coverage_percent: float,
    severity_heuristic: str,
    guided_observations: GuidedObservations | None = None,
    runtime_mode: str | None = None,
    sample_id: str | None = None,
) -> dict[str, Any]:
    mode = get_runtime_mode(runtime_mode)
    sample_identifier = sample_id or f"request-{uuid4().hex}"
    cnn = CNNOutput(
        sample_id=sample_identifier,
        predicted_class=top_label,
        confidence=top_confidence,
        second_class=second_label,
        second_confidence=second_confidence,
        class_probabilities=cnn_probabilities,
    )
    guided_override = _environment_flag_enabled(
        "ALLOW_UNVALIDATED_GUIDED_OBSERVATIONS", default=False
    )
    sample, observation_result = prepare_observations(
        cnn,
        guided_observations,
        attention_coverage_percent,
        severity_heuristic,
        runtime_mode=mode,
        allow_unvalidated_guided=guided_override,
    )
    safety = evaluate_safety(
        top_label=top_label,
        top_confidence=top_confidence,
        second_label=second_label,
        second_confidence=second_confidence,
        attention_coverage_percent=attention_coverage_percent,
    )
    symbolic = reasoning_engine(sample, mode=mode)
    raw_phase7_fusion = fuse_predictions(
        {
            "sample_id": sample_identifier,
            "predicted_class": sample["cnn_prediction"]["predicted_class"],
            "confidence": top_confidence,
            "class_probabilities": canonical_probabilities_to_research(
                cnn_probabilities
            ),
        },
        symbolic,
    )
    fusion, abstention_policy_applied = _apply_runtime_fusion_policy(
        raw_phase7_fusion, symbolic, cnn_probabilities
    )
    diagnostic = resolve_diagnostic_conflict(fusion, symbolic, safety)
    candidate_key = diagnostic["candidate_prediction"]
    management = resolve_management_rules(
        final_class=candidate_key,
        runtime_mode=mode,
        safety_safeguards=safety["safeguards"],
    )
    observation_trace_event = {
        "event": "observation_vocabulary_validation",
        "vocabulary_version": "1.0.0",
        "fields": observation_result["observation_validation"],
    }
    explanation = build_explanation(
        diagnostic_result=diagnostic,
        fusion_result=fusion,
        symbolic_result=symbolic,
        observation_result=observation_result,
    )
    explanation["reasoning_trace"] = [
        observation_trace_event,
        *explanation["reasoning_trace"],
    ]
    symbolic_canonical = (
        None
        if symbolic["symbolic_prediction"] == "Uncertain"
        else to_canonical_key(symbolic["symbolic_prediction"])
    )
    return {
        "api_version": "2.0.0",
        "runtime_mode": mode,
        "artifact_versions": artifact_info(),
        "cnn_result": {
            "prediction": top_label,
            "display_name": display_name(top_label),
            "confidence": round(top_confidence, 4),
            "second_prediction": second_label,
            "second_confidence": round(second_confidence, 4),
            "probabilities": {
                key: round(cnn_probabilities[key], 4) for key in CNN_CLASS_ORDER
            },
            "reliability": fusion["cnn"]["reliability"],
        },
        "observation_result": observation_result,
        "visual_evidence": {
            "attention_coverage_percent": round(attention_coverage_percent, 2),
            "severity_heuristic": severity_heuristic,
            "segmentation_validated": False,
            "disclaimer": GRADCAM_DISCLAIMER,
        },
        "safety_result": safety,
        "symbolic_result": {
            "status": symbolic["status"],
            "prediction": symbolic_canonical,
            "research_prediction": symbolic["symbolic_prediction"],
            "score": symbolic["symbolic_score"],
            "reliability": fusion["symbolic"]["reliability"],
            "confidence_category": symbolic["confidence_label"],
            "disease_scores": research_probabilities_to_canonical(
                symbolic["disease_scores"]
            ),
            "matched_rule_count": symbolic["matched_rule_count"],
            "matched_rule_ids": symbolic["matched_rule_ids"],
            "matched_rules": symbolic["matched_rules"],
            "matched_evidence_ids": symbolic["matched_evidence_ids"],
            "observations_used": symbolic["observations_used"],
            "reasoning_trace": [
                observation_trace_event,
                *symbolic["reasoning_trace"],
            ],
            "limitations": symbolic["limitations"],
            "warnings": [
                *[item for item in symbolic["warnings"] if item],
                *observation_result["warnings"],
            ],
        },
        "fusion_result": {
            "final_prediction": diagnostic["final_prediction"],
            "display_name": (
                display_name(diagnostic["final_prediction"])
                if diagnostic["final_prediction"] is not None
                else "Uncertain"
            ),
            "candidate_prediction": candidate_key,
            "candidate_display_name": display_name(candidate_key),
            "final_confidence": fusion["fusion"]["final_confidence"],
            "cnn_weight": fusion["fusion"]["cnn_weight"],
            "symbolic_weight": fusion["fusion"]["symbolic_weight"],
            "raw_phase7_cnn_weight": raw_phase7_fusion["fusion"]["cnn_weight"],
            "raw_phase7_symbolic_weight": raw_phase7_fusion["fusion"][
                "symbolic_weight"
            ],
            "raw_phase7_class_scores": research_probabilities_to_canonical(
                raw_phase7_fusion["fusion"]["class_scores"]
            ),
            "abstention_policy_applied": abstention_policy_applied,
            "class_scores": research_probabilities_to_canonical(
                fusion["fusion"]["class_scores"]
            ),
            "agreement_status": diagnostic["status"],
            "conflict_status": (
                "detected" if diagnostic["conflict_detected"] else "none"
            ),
            "decision_status": fusion["fusion"]["decision_status"],
            "requires_manual_review": diagnostic["requires_manual_review"],
            "resolution": diagnostic["resolution"],
        },
        "management_result": management,
        "explanation": explanation,
    }
