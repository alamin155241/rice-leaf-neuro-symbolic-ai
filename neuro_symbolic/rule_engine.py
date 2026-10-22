"""Deprecated safety-only adapter for the pre-v2 rule-engine interface.

This module deliberately performs no symbolic diagnosis. The authoritative
interfaces are ``reasoning_engine``, ``fuse_predictions``, and
``orchestrate_diagnosis``. Legacy phenotype and knowledge-rule arguments are
accepted only so older callers fail safely during migration; their values are
never used as observed or matched evidence.
"""

from __future__ import annotations

import warnings
from typing import Any

from .safety_layer import evaluate_safety


def evaluate_prediction_rules(
    *,
    top_label: str,
    top_confidence: float,
    second_label: str,
    second_confidence: float,
    severity: str,
    attention_coverage_percent: float,
    phenotype_knowledge: dict[str, Any] | None = None,
    applicable_knowledge_rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return legacy-shaped deterministic safety output only.

    ``phenotype_knowledge`` and ``applicable_knowledge_rules`` are intentionally
    ignored to prevent class-derived phenotype claims and a competing rule path.
    """
    del phenotype_knowledge, applicable_knowledge_rules
    warnings.warn(
        "evaluate_prediction_rules is deprecated and now returns safety-only "
        "compatibility output; use orchestrate_diagnosis instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    safety = evaluate_safety(
        top_label=top_label,
        top_confidence=top_confidence,
        second_label=second_label,
        second_confidence=second_confidence,
        attention_coverage_percent=attention_coverage_percent,
    )
    if safety["force_uncertainty"]:
        final_decision = "uncertain"
        trust_level = "low"
    elif safety["ambiguity_detected"]:
        final_decision = f"possible_{top_label}_or_{second_label}"
        trust_level = "medium"
    else:
        final_decision = top_label
        trust_level = (
            "high"
            if top_confidence >= 0.90 and safety["probability_gap"] >= 0.15
            else "medium"
        )
    matched_rules = [dict(rule) for rule in safety["safeguards"]]
    return {
        "final_decision": final_decision,
        "trust_level": trust_level,
        "matched_rules": matched_rules,
        "candidate_recommendations": [
            rule["recommendation"] for rule in matched_rules
        ],
        "candidate_warnings": [rule["warning"] for rule in matched_rules],
        "reasoning_notes": [
            "Deprecated compatibility adapter: no symbolic diagnosis was run.",
            *safety["warnings"],
            f"Confidence: {top_confidence:.4f}",
            f"Second guess: {second_label} ({second_confidence:.4f})",
            (
                "Grad-CAM attention coverage: "
                f"{attention_coverage_percent:.2f}% "
                "(heuristic; not validated lesion segmentation)"
            ),
            f"Reported severity: {severity}",
        ],
        "phenotype_facts": [],
        "knowledge_sources": [],
        "ambiguity_detected": safety["ambiguity_detected"],
        "contradiction_detected": safety["contradiction_detected"],
        "deprecated_adapter": True,
        "symbolic_diagnosis_performed": False,
    }
