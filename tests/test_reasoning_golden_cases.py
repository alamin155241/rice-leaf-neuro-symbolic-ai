"""Semantic successors to the original permissive Phase 6 golden cases.

The stored notebook snapshots are retained as historical artifacts. They are
not a correctness oracle for runtime matching because they include the unsafe
token averaging, conclusion matching, and CNN-label parity path.
"""

import pytest

from neuro_symbolic.reasoning_engine import reasoning_engine


CASES = [
    (
        "TEST_LEAF_BLAST_001",
        {
            "lesion_present": True,
            "lesion_shape": "elliptical spindle",
            "lesion_center_color": "gray white",
            "lesion_margin_color": "brown reddish brown",
            "leaf_region": "leaf blade",
            "other_observations": [
                "leaf blast spot present",
                "acute lesion with gray white center",
            ],
        },
        "Leaf Blast",
    ),
    (
        "TEST_BROWN_SPOT_001",
        {
            "lesion_present": True,
            "lesion_shape": "oval",
            "lesion_color": "brown",
            "necrosis_present": True,
            "lesion_center_color": "gray white",
            "leaf_region": "leaf blade",
            "halo_present": True,
            "halo_color": "yellow chlorotic",
            "other_observations": [
                "fully developed leaf spots",
                "oval necrotic lesion",
                "chlorotic halo",
            ],
        },
        "Brown Spot",
    ),
    (
        "TEST_LEAF_SCALD_001",
        {
            "lesion_present": True,
            "lesion_shape": "oblong",
            "leaf_region": "leaf tip leaf edge",
            "halo_present": True,
            "halo_color": "light brown",
            "zonation_present": True,
            "leaf_age": "mature leaf",
        },
        "Leaf Scald",
    ),
    (
        "TEST_NBLS_001",
        {
            "lesion_present": True,
            "lesion_shape": "narrow elongated",
            "lesion_color": "light brown",
            "lesion_width_mm": 1.0,
            "leaf_region": "leaf blade",
            "other_observations": ["narrow brown lesions observed"],
        },
        "Narrow Brown Leaf Spot",
    ),
    (
        "TEST_HEALTHY_001",
        {
            "lesion_present": False,
            "visual_status": "visibly healthy",
            "vigor": "high vigor",
            "other_observations": [
                "lacks spindle shaped lesions",
                "lacks dark brown dots",
            ],
        },
        "Healthy Rice Leaf",
    ),
]


@pytest.mark.parametrize("sample_id,visual_features,expected", CASES)
def test_semantic_golden_cases(sample_id, visual_features, expected):
    result = reasoning_engine(
        {
            "sample_id": sample_id,
            "cnn_prediction": {"predicted_class": "Brown Spot"},
            "visual_features": visual_features,
            "environment_context": {"enabled": False},
        },
        "research",
    )
    assert result["symbolic_prediction"] == expected
    assert "brown spot" not in result["observations_used"]


def test_runtime_does_not_use_cnn_label_as_symbolic_observation():
    result = reasoning_engine(
        {
            "sample_id": "anti-circular",
            "cnn_prediction": {"predicted_class": "Leaf Blast"},
            "visual_features": {},
            "environment_context": {"enabled": False},
        },
        "research",
        include_cnn_label_for_parity=True,
    )
    assert result["status"] == "insufficient_observation_evidence"
    assert result["matched_rule_count"] == 0
    assert "leaf blast" not in result["observations_used"]


def test_trace_exposes_semantic_policy_without_matching_conclusions():
    result = reasoning_engine(
        {
            "sample_id": "semantic-trace",
            "visual_features": {
                "lesion_shape": "oblong",
                "halo_color": "light brown",
            },
            "environment_context": {"enabled": False},
        },
        "research",
    )
    trace = next(
        item
        for item in result["reasoning_trace"]
        if item["rule_id"] == "EA_RULE_CDDC7A936F"
    )
    assert trace["fired"] is True
    assert trace["score_eligible"] is True
    assert trace["match"]["condition_logic"] == "ALL_MANDATORY"
    assert trace["match"]["conclusion_used_for_firing"] is False
    assert trace["match"]["conclusion_score"] == 0.0
