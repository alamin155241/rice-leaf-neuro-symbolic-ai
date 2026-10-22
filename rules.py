"""Deprecated compatibility wrapper for the original symbolic-rule API.

The active rule implementation lives in ``neuro_symbolic`` and
``conflict_resolution``. This module intentionally contains no disease guidance
of its own, so stale three-class rules cannot compete with the current system.
"""

from __future__ import annotations

from typing import Any
from warnings import warn

from conflict_resolution import resolve_rule_conflicts
from knowledge_base import get_applicable_rules
from knowledge_graph import get_phenotype_knowledge
from neuro_symbolic import evaluate_prediction_rules


def apply_symbolic_rules(
    predicted_label: str, confidence: float
) -> dict[str, Any]:
    """Call the current reasoning pipeline using the legacy two-argument API."""
    warn(
        "rules.apply_symbolic_rules is deprecated; use the neuro_symbolic and "
        "conflict_resolution modules directly.",
        DeprecationWarning,
        stacklevel=2,
    )
    severity = "none" if predicted_label == "healthy" else "mild"
    knowledge_rules = get_applicable_rules(predicted_label, severity, confidence)
    symbolic = evaluate_prediction_rules(
        top_label=predicted_label,
        top_confidence=confidence,
        second_label="unknown",
        second_confidence=0.0,
        severity=severity,
        attention_coverage_percent=0.0,
        phenotype_knowledge=get_phenotype_knowledge(predicted_label),
        applicable_knowledge_rules=knowledge_rules,
    )
    resolution = resolve_rule_conflicts(
        symbolic["matched_rules"],
        disease=predicted_label,
        severity=severity,
        confidence=confidence,
    )

    status = {
        "low": "Uncertain",
        "medium": "Needs Review",
        "high": "High Confidence",
    }[symbolic["trust_level"]]
    return {
        "symbolic_status": status,
        "final_label": symbolic["final_decision"],
        "explanation": " ".join(symbolic["reasoning_notes"]),
        "recommendation": resolution["selected_recommendation"],
        "warning": resolution["selected_warning"],
        "matched_rules": symbolic["matched_rules"],
        "conflict_resolution": resolution,
    }
