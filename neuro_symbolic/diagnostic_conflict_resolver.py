"""Diagnostic decision semantics layered on the exact Phase 7 fusion result."""

from __future__ import annotations

from typing import Any

from .class_mapping import to_canonical_key


def resolve_diagnostic_conflict(
    fusion_result: dict[str, Any],
    symbolic_result: dict[str, Any],
    safety_result: dict[str, Any],
) -> dict[str, Any]:
    fusion = fusion_result["fusion"]
    conflict = fusion_result["conflict"]
    symbolic_status = symbolic_result.get("status")
    symbolic_abstained = symbolic_status == "insufficient_observation_evidence"

    if safety_result.get("force_uncertainty"):
        status = "safety_forced_uncertainty"
        final_prediction = None
        resolution = (
            "The diagnostic label was withheld by deterministic safety policy; "
            "retake or manual review is required."
        )
    elif symbolic_abstained:
        status = "symbolic_abstention"
        final_prediction = to_canonical_key(fusion["final_prediction"])
        resolution = (
            "Structured phenotype observations were unavailable. The fused "
            "result therefore relies on CNN evidence; symbolic reliability is zero."
        )
    elif fusion["decision_status"] == "AGREEMENT":
        status = (
            "low_confidence_agreement"
            if fusion["final_confidence"] < 0.60
            else "agreement"
        )
        final_prediction = to_canonical_key(fusion["final_prediction"])
        resolution = conflict["resolution"]
    elif fusion["decision_status"] == "CONFLICT_RESOLVED":
        status = "cnn_symbolic_disagreement"
        final_prediction = to_canonical_key(fusion["final_prediction"])
        resolution = conflict["resolution"]
    elif fusion["decision_status"] in {"UNCERTAIN", "AMBIGUOUS"}:
        status = "unresolved_conflict"
        final_prediction = None
        resolution = conflict["resolution"]
    else:
        status = fusion["decision_status"].lower()
        final_prediction = to_canonical_key(fusion["final_prediction"])
        resolution = conflict["resolution"]

    return {
        "status": status,
        "final_prediction": final_prediction,
        "candidate_prediction": to_canonical_key(fusion["final_prediction"]),
        "final_confidence": fusion["final_confidence"],
        "conflict_detected": bool(conflict["detected"]),
        "symbolic_abstained": symbolic_abstained,
        "requires_manual_review": bool(
            safety_result.get("requires_manual_review")
            or status == "unresolved_conflict"
        ),
        "resolution": resolution,
    }
