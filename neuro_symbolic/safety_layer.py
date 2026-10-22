"""Deterministic inference safeguards, separate from scientific rule evidence."""

from __future__ import annotations

from typing import Any


# Retained from the working prototype where Phase 6/7 do not define equivalents.
LOW_CONFIDENCE_THRESHOLD = 0.60
AMBIGUITY_GAP_THRESHOLD = 0.08
HEALTHY_ATTENTION_CONTRADICTION_THRESHOLD = 6.0


def evaluate_safety(
    *,
    top_label: str,
    top_confidence: float,
    second_label: str,
    second_confidence: float,
    attention_coverage_percent: float,
) -> dict[str, Any]:
    """Return application safeguards without treating them as phenotype evidence."""
    gap = top_confidence - second_confidence
    low_confidence = top_confidence < LOW_CONFIDENCE_THRESHOLD
    ambiguity = gap < AMBIGUITY_GAP_THRESHOLD
    contradiction = (
        top_label == "healthy"
        and attention_coverage_percent
        > HEALTHY_ATTENTION_CONTRADICTION_THRESHOLD
    )
    brown_blast_caution = {top_label, second_label} == {
        "brown_spot",
        "leaf_blast",
    }
    warnings: list[str] = []
    safeguards: list[dict[str, Any]] = []

    if low_confidence:
        warnings.append(
            f"CNN confidence {top_confidence:.4f} is below the retained "
            f"system threshold {LOW_CONFIDENCE_THRESHOLD:.2f}."
        )
        safeguards.append(_safeguard("SYS_LOW_CONFIDENCE", warnings[-1]))
    if ambiguity:
        warnings.append(
            f"The top-two CNN gap {gap:.4f} is below the retained system "
            f"threshold {AMBIGUITY_GAP_THRESHOLD:.2f}."
        )
        safeguards.append(_safeguard("SYS_TOP_TWO_AMBIGUITY", warnings[-1]))
    if contradiction:
        warnings.append(
            "A healthy CNN prediction has unusually high Grad-CAM attention "
            "coverage. Grad-CAM is not lesion segmentation; manual review is required."
        )
        safeguards.append(
            _safeguard("SYS_HEALTHY_ATTENTION_CONTRADICTION", warnings[-1])
        )
    if brown_blast_caution:
        warnings.append(
            "Brown Spot and Leaf Blast are the top two CNN classes; inspect "
            "additional leaves or seek expert review before management action."
        )

    return {
        "low_confidence": low_confidence,
        "ambiguity_detected": ambiguity,
        "contradiction_detected": contradiction,
        "brown_spot_leaf_blast_caution": brown_blast_caution,
        "probability_gap": round(gap, 4),
        "warnings": warnings,
        "requires_manual_review": bool(low_confidence or ambiguity or contradiction),
        "force_uncertainty": bool(low_confidence or contradiction),
        "safeguards": safeguards,
        "policy_provenance": "system_inference_safety_policy",
        "scientific_rule_evidence": False,
    }


def _safeguard(rule_id: str, warning: str) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "validation_status": "system_safety_rule",
        "runtime_state": "SYSTEM_POLICY",
        "actionable": True,
        "advisory_only": False,
        "recommendation": (
            "Retake the image under clear lighting and consult a local "
            "agricultural expert if uncertainty persists."
        ),
        "warning": warning,
        "source": "system_inference_safety_policy",
        "notes": (
            "Deterministic application safeguard; not expert-validated "
            "phenotype or agronomic evidence."
        ),
    }
