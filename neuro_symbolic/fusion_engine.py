"""Exact Phase 7 adaptive reliability-weighted fusion functions."""

from __future__ import annotations

from typing import Any

import numpy as np

from .artifact_loader import load_json_artifact


def _config() -> dict[str, Any]:
    return load_json_artifact("phase7_fusion_config")


def normalize_probability_dict(values: dict[str, float]) -> dict[str, float]:
    classes = _config()["classes"]
    cleaned = {key: float(values.get(key, 0.0)) for key in classes}
    total = sum(max(0.0, value) for value in cleaned.values())
    if total <= 0:
        return {key: 0.0 for key in classes}
    return {key: max(0.0, cleaned[key]) / total for key in classes}


def top_two(values: dict[str, float]) -> tuple[tuple[str, float], tuple[str, float]]:
    ordered = sorted(values.items(), key=lambda item: item[1], reverse=True)
    return ordered[0], ordered[1] if len(ordered) > 1 else ("", 0.0)


def normalized_entropy(values: dict[str, float]) -> float:
    classes = _config()["classes"]
    probabilities = np.array(
        [max(1e-12, values[key]) for key in classes], dtype=float
    )
    probabilities /= probabilities.sum()
    return float(
        -np.sum(probabilities * np.log(probabilities)) / np.log(len(classes))
    )


def cnn_reliability(probabilities: dict[str, float]) -> dict[str, Any]:
    config = _config()["cnn_reliability_formula"]
    (top_class, top_probability), (_, second_probability) = top_two(probabilities)
    margin = top_probability - second_probability
    entropy = normalized_entropy(probabilities)
    reliability = (
        config["top_probability_weight"] * top_probability
        + config["margin_weight"] * margin
        + config["inverse_entropy_weight"] * (1.0 - entropy)
    )
    return {
        "top_class": top_class,
        "top_probability": round(top_probability, 4),
        "margin": round(margin, 4),
        "entropy": round(entropy, 4),
        "reliability": round(max(0.0, min(1.0, reliability)), 4),
    }


def symbolic_reliability(result: dict[str, Any]) -> dict[str, Any]:
    config = _config()["symbolic_reliability_formula"]
    top_score = float(result.get("symbolic_score", 0.0))
    margin = float(result.get("score_margin", 0.0))
    matched = int(result.get("matched_rule_count", 0))
    rule_support = min(1.0, matched / 4.0)
    reliability = (
        config["top_score_weight"] * top_score
        + config["margin_weight"] * margin
        + config["rule_support_weight"] * rule_support
    )
    label = result.get("confidence_label", "")
    if label == "INSUFFICIENT_SYMBOLIC_EVIDENCE":
        reliability = 0.0
    elif label == "LOW_OR_CONFLICTED":
        reliability *= 0.70
    return {
        "top_class": result.get("symbolic_prediction", "Uncertain"),
        "top_score": round(top_score, 4),
        "margin": round(margin, 4),
        "matched_rule_count": matched,
        "reliability": round(max(0.0, min(1.0, reliability)), 4),
    }


def adaptive_weights(
    cnn_info: dict[str, Any], symbolic_info: dict[str, Any]
) -> dict[str, Any]:
    cnn_reliability_value = cnn_info["reliability"]
    symbolic_reliability_value = symbolic_info["reliability"]
    total = cnn_reliability_value + symbolic_reliability_value
    if total <= 0:
        return {
            "cnn_weight": 0.5,
            "symbolic_weight": 0.5,
            "weight_reason": "Both modalities have insufficient reliability.",
        }
    cnn_weight = cnn_reliability_value / total
    bounds = _config()["weight_bounds"]
    cnn_weight = min(
        bounds["maximum_modality_weight"],
        max(bounds["minimum_modality_weight"], cnn_weight),
    )
    symbolic_weight = 1.0 - cnn_weight
    if cnn_reliability_value > symbolic_reliability_value + 0.20:
        reason = "CNN reliability clearly exceeded symbolic reliability."
    elif symbolic_reliability_value > cnn_reliability_value + 0.20:
        reason = "Symbolic reliability clearly exceeded CNN reliability."
    else:
        reason = "CNN and symbolic reliability were comparable."
    return {
        "cnn_weight": round(cnn_weight, 4),
        "symbolic_weight": round(symbolic_weight, 4),
        "weight_reason": reason,
    }


def fuse_predictions(
    cnn_output: dict[str, Any], symbolic_output: dict[str, Any]
) -> dict[str, Any]:
    cnn_probabilities = normalize_probability_dict(
        cnn_output.get("class_probabilities", {})
    )
    symbolic_scores = normalize_probability_dict(
        symbolic_output.get("disease_scores", {})
    )
    cnn_info = cnn_reliability(cnn_probabilities)
    symbolic_info = symbolic_reliability(symbolic_output)
    weights = adaptive_weights(cnn_info, symbolic_info)
    fused_scores = normalize_probability_dict(
        {
            class_name: (
                weights["cnn_weight"] * cnn_probabilities[class_name]
                + weights["symbolic_weight"] * symbolic_scores[class_name]
            )
            for class_name in _config()["classes"]
        }
    )
    (final_class, final_score), (second_class, second_score) = top_two(fused_scores)
    conflict = (
        cnn_info["top_class"] != symbolic_info["top_class"]
        and symbolic_info["top_class"] != "Uncertain"
    )
    final_margin = final_score - second_score
    thresholds = _config()["uncertainty_thresholds"]
    if final_score < thresholds["minimum_final_confidence"]:
        status = "UNCERTAIN"
    elif final_margin < thresholds["minimum_final_margin"]:
        status = "AMBIGUOUS"
    elif conflict:
        status = "CONFLICT_RESOLVED"
    else:
        status = "AGREEMENT"
    if status == "AGREEMENT":
        resolution = "CNN and symbolic reasoning supported the same diagnosis."
    elif status == "CONFLICT_RESOLVED":
        winner = (
            "CNN"
            if weights["cnn_weight"] > weights["symbolic_weight"]
            else "symbolic reasoning"
        )
        resolution = (
            f"Conflict was resolved in favor of {winner} using adaptive "
            "reliability weighting."
        )
    elif status == "AMBIGUOUS":
        resolution = (
            "The top fused classes were too close; the result should be reviewed "
            "or retested."
        )
    else:
        resolution = "Combined evidence was insufficient for a confident diagnosis."
    return {
        "sample_id": cnn_output.get(
            "sample_id", symbolic_output.get("sample_id", "")
        ),
        "cnn": {
            "prediction": cnn_info["top_class"],
            "probability": cnn_info["top_probability"],
            "reliability": cnn_info["reliability"],
            "margin": cnn_info["margin"],
            "entropy": cnn_info["entropy"],
            "class_probabilities": {
                key: round(value, 4) for key, value in cnn_probabilities.items()
            },
        },
        "symbolic": {
            "prediction": symbolic_info["top_class"],
            "score": symbolic_info["top_score"],
            "reliability": symbolic_info["reliability"],
            "margin": symbolic_info["margin"],
            "matched_rule_count": symbolic_info["matched_rule_count"],
            "disease_scores": symbolic_scores,
        },
        "fusion": {
            **weights,
            "class_scores": {
                key: round(value, 4) for key, value in fused_scores.items()
            },
            "final_prediction": final_class,
            "final_confidence": round(final_score, 4),
            "second_choice": second_class,
            "second_choice_score": round(second_score, 4),
            "final_margin": round(final_margin, 4),
            "decision_status": status,
        },
        "conflict": {
            "detected": bool(conflict),
            "cnn_prediction": cnn_info["top_class"],
            "symbolic_prediction": symbolic_info["top_class"],
            "resolution": resolution,
        },
    }
