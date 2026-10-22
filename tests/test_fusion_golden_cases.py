import json
from pathlib import Path

import pytest

from neuro_symbolic.fusion_engine import fuse_predictions


PHASE7 = Path(__file__).resolve().parent / "golden_data" / "phase7"


@pytest.mark.parametrize(
    "expected",
    json.loads((PHASE7 / "fusion_results_v1.json").read_text(encoding="utf-8")),
)
def test_phase7_fusion_golden_cases(expected):
    symbolic = {
        "symbolic_prediction": expected["symbolic"]["prediction"],
        "symbolic_score": expected["symbolic"]["score"],
        "score_margin": expected["symbolic"]["margin"],
        "matched_rule_count": expected["symbolic"]["matched_rule_count"],
        "confidence_label": expected["explanation"]["reasoning_confidence_label"],
        "disease_scores": expected["symbolic"]["disease_scores"],
    }
    actual = fuse_predictions(
        {
            "sample_id": expected["sample_id"],
            "class_probabilities": expected["cnn"]["class_probabilities"],
        },
        symbolic,
    )
    assert actual["cnn"]["reliability"] == expected["cnn"]["reliability"]
    assert actual["symbolic"]["reliability"] == expected["symbolic"]["reliability"]
    assert actual["fusion"] == expected["fusion"]
    assert actual["conflict"] == expected["conflict"]


@pytest.mark.parametrize(
    "expected",
    json.loads(
        (PHASE7 / "conflict_stress_test_results_v1.json").read_text(encoding="utf-8")
    ),
)
def test_phase7_conflict_stress_golden_cases(expected):
    symbolic = {
        "symbolic_prediction": expected["symbolic"]["prediction"],
        "symbolic_score": expected["symbolic"]["score"],
        "score_margin": expected["symbolic"]["margin"],
        "matched_rule_count": expected["symbolic"]["matched_rule_count"],
        "confidence_label": (
            "INSUFFICIENT_SYMBOLIC_EVIDENCE"
            if expected["symbolic"]["prediction"] == "Uncertain"
            else "HIGH"
            if expected["symbolic"]["reliability"] > 0.8
            else "LOW_OR_CONFLICTED"
        ),
        "disease_scores": expected["symbolic"]["disease_scores"],
    }
    actual = fuse_predictions(
        {
            "sample_id": expected["sample_id"],
            "class_probabilities": expected["cnn"]["class_probabilities"],
        },
        symbolic,
    )
    assert actual["fusion"] == expected["fusion"]
    assert actual["conflict"] == expected["conflict"]
