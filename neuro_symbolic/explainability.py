"""Constrained, evidence-traceable explanation templates."""

from __future__ import annotations

from typing import Any

from .class_mapping import display_name


GRADCAM_DISCLAIMER = (
    "Grad-CAM shows model attention, not validated lesion segmentation. "
    "Attention coverage is a thresholded heuristic and is not exact infected area."
)


def build_explanation(
    *,
    diagnostic_result: dict[str, Any],
    fusion_result: dict[str, Any],
    symbolic_result: dict[str, Any],
    observation_result: dict[str, Any],
) -> dict[str, Any]:
    final_key = diagnostic_result.get("final_prediction")
    candidate_key = diagnostic_result["candidate_prediction"]
    rules = symbolic_result.get("matched_rules", [])
    citations = sorted(
        {
            str(rule.get("citation"))
            for rule in rules
            if rule.get("citation")
        }
    )
    source_records = [
        {
            "rule_id": rule.get("rule_id"),
            "master_record_id": rule.get("master_record_id"),
            "source_record_id": rule.get("source_record_id"),
            "source_document_id": rule.get("source_document_id"),
            "runtime_state": rule.get("runtime_state"),
            "validation": rule.get("validation"),
        }
        for rule in rules
    ]
    matched_observations = sorted(
        {
            str(observation)
            for rule in rules
            for observation in rule.get("match", {}).get(
                "matched_observations", []
            )
            if str(observation).strip()
        }
    )
    if diagnostic_result["symbolic_abstained"]:
        symbolic_text = (
            "Symbolic reasoning abstained and made no effective contribution "
            "because sufficient structured phenotype observations were unavailable."
        )
    else:
        symbolic_text = (
            f"Symbolic reasoning contributed {fusion_result['fusion']['symbolic_weight']:.4f} "
            f"weight from {symbolic_result.get('matched_rule_count', 0)} matched rules."
        )
    if diagnostic_result["status"] == "safety_forced_uncertainty":
        summary = (
            "Diagnosis withheld because deterministic safety safeguards require "
            "retesting or manual review. CNN/fusion candidate: "
            f"{display_name(candidate_key)} "
            f"({diagnostic_result['final_confidence']:.4f})."
        )
    elif final_key is None:
        summary = (
            "Diagnosis withheld because the fused evidence remains uncertain or "
            "ambiguous. CNN/fusion candidate: "
            f"{display_name(candidate_key)} "
            f"({diagnostic_result['final_confidence']:.4f})."
        )
    else:
        summary = (
            f"Final diagnosis: {display_name(final_key)} "
            f"({diagnostic_result['final_confidence']:.4f})."
        )
    return {
        "summary": summary,
        "provided_observed_features": observation_result.get(
            "provided_observed_features", []
        ),
        "matched_observed_features": matched_observations,
        "matched_rule_ids": symbolic_result.get("matched_rule_ids", []),
        "evidence_ids": symbolic_result.get("matched_evidence_ids", []),
        "citations": citations,
        "source_records": source_records,
        "why_cnn_contributed": (
            f"CNN reliability was {fusion_result['cnn']['reliability']:.4f}; "
            f"adaptive CNN weight was {fusion_result['fusion']['cnn_weight']:.4f}."
        ),
        "why_symbolic_contributed": symbolic_text,
        "why_final_prediction_was_selected": diagnostic_result["resolution"],
        "reasoning_trace": symbolic_result.get("reasoning_trace", []),
        "limitations": [
            *symbolic_result.get("limitations", []),
            "Guided categorical values are accepted only from the provenance-backed "
            "vocabulary; explicitly identified free-text fields remain unvalidated.",
            GRADCAM_DISCLAIMER,
            "This software integration does not establish improved diagnostic accuracy.",
            "Results do not replace agronomist or plant-pathologist assessment.",
        ],
    }
