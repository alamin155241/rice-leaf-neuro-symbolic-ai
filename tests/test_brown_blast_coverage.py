import pytest

from neuro_symbolic.artifact_loader import load_rules
from neuro_symbolic.orchestrator import orchestrate_diagnosis
from neuro_symbolic.reasoning_engine import (
    CONDITION_CONTRADICTION,
    CONDITION_NOT_PROVIDED,
    reasoning_engine,
)
from neuro_symbolic.schemas import GuidedObservations


BROWN_RULE_ID = "EA_RULE_30859DE496"
BLAST_RULE_ID = "EA_RULE_2516F683E3"
CNN = {
    "brown_spot": 0.20,
    "healthy": 0.20,
    "leaf_blast": 0.20,
    "leaf_scald": 0.20,
    "narrow_brown_spot": 0.20,
}


def _reason(visual):
    return reasoning_engine(
        {"visual_features": visual, "environment_context": {"enabled": False}},
        "research",
    )


def _trace(result, rule_id):
    return next(
        item for item in result["reasoning_trace"] if item["rule_id"] == rule_id
    )


def _orchestrate(guided):
    return orchestrate_diagnosis(
        cnn_probabilities=CNN,
        top_label="brown_spot",
        top_confidence=0.20,
        second_label="leaf_blast",
        second_confidence=0.20,
        attention_coverage_percent=5.0,
        severity_heuristic="moderate",
        guided_observations=guided,
        runtime_mode="research",
        sample_id="brown-blast-coverage",
    )


def test_compiled_rules_are_research_only_and_trace_existing_records():
    rules = {rule["rule_id"]: rule for rule in load_rules()}
    brown = rules[BROWN_RULE_ID]
    blast = rules[BLAST_RULE_ID]
    for rule in (brown, blast):
        assert rule["runtime_state"] == "EVIDENCE_SUPPORTED_HOLD"
        assert rule["runtime_enabled"] is False
        assert rule["validation"]["implementation_status"] == (
            "RESEARCH_ONLY_COMPILED_RULE"
        )
        assert rule["provenance"]["evidence_ids"] == []
    assert brown["provenance"]["master_record_ids"] == ["MKI_0914"]
    assert brown["provenance"]["implementation_record_ids"] == [
        "BSP_IMPL_293"
    ]
    assert blast["provenance"]["master_record_ids"] == [
        "MKI_0229",
        "MKI_0230",
    ]
    assert blast["provenance"]["implementation_record_ids"] == [
        "RBL_IMPL_229",
        "RBL_IMPL_230",
    ]
    assert brown["provenance"]["source_document_id"] == "IRRI2018_FFD"
    assert blast["provenance"]["source_document_id"] == "IRRI2018_FFD"
    assert brown["provenance"]["citation"] == rules[
        "EA_RULE_EE3FB34441"
    ]["provenance"]["citation"]
    assert blast["provenance"]["citation"] == rules[
        "EA_RULE_610FE9355D"
    ]["provenance"]["citation"]


def test_brown_spot_complete_structured_phenotype_scores_and_has_reliability():
    guided = GuidedObservations(
        leaf_region="leaf_blade",
        lesion_shape="oval",
        necrosis_present=True,
        halo_color="yellow",
    )
    result = _orchestrate(guided)
    symbolic = result["symbolic_result"]
    assert symbolic["research_prediction"] == "Brown Spot"
    assert BROWN_RULE_ID in symbolic["matched_rule_ids"]
    assert symbolic["score"] > 0
    assert symbolic["reliability"] > 0


def test_brown_spot_missing_necrosis_does_not_fire():
    result = _reason(
        {
            "leaf_region": "leaf_blade",
            "lesion_shape": "oval",
            "halo_color": "yellow",
        }
    )
    trace = _trace(result, BROWN_RULE_ID)
    assert trace["fired"] is False
    assert trace["match"]["condition_states"][2]["state"] == (
        CONDITION_NOT_PROVIDED
    )
    assert BROWN_RULE_ID not in result["matched_rule_ids"]


def test_brown_spot_necrosis_absent_is_a_contradiction():
    result = _reason(
        {
            "leaf_region": "leaf_blade",
            "lesion_shape": "oval",
            "necrosis_present": False,
            "halo_color": "yellow",
        }
    )
    trace = _trace(result, BROWN_RULE_ID)
    assert trace["fired"] is False
    assert trace["match"]["condition_states"][2]["state"] == (
        CONDITION_CONTRADICTION
    )


def test_brown_spot_missing_yellow_halo_does_not_fire():
    result = _reason(
        {
            "leaf_region": "leaf_blade",
            "lesion_shape": "oval",
            "necrosis_present": True,
        }
    )
    trace = _trace(result, BROWN_RULE_ID)
    assert trace["fired"] is False
    assert trace["match"]["condition_states"][3]["state"] == (
        CONDITION_NOT_PROVIDED
    )


@pytest.mark.parametrize("center", ["gray", "white"])
def test_leaf_blast_complete_structured_phenotype_fires(center):
    result = _reason(
        {
            "lesion_shape": "spindle_shaped",
            "lesion_center_color": center,
            "lesion_margin_color": "brown",
        }
    )
    assert result["symbolic_prediction"] == "Leaf Blast"
    assert BLAST_RULE_ID in result["matched_rule_ids"]
    assert _trace(result, BLAST_RULE_ID)["score_eligible"] is True


def test_leaf_blast_missing_margin_does_not_fire():
    result = _reason(
        {
            "lesion_shape": "spindle_shaped",
            "lesion_center_color": "gray",
        }
    )
    trace = _trace(result, BLAST_RULE_ID)
    assert trace["fired"] is False
    assert trace["match"]["condition_states"][2]["state"] == (
        CONDITION_NOT_PROVIDED
    )


def test_typical_brown_spot_does_not_fire_leaf_blast_rule():
    result = _reason(
        {
            "leaf_region": "leaf_blade",
            "lesion_shape": "oval",
            "necrosis_present": True,
            "halo_color": "yellow",
        }
    )
    assert result["symbolic_prediction"] == "Brown Spot"
    assert BLAST_RULE_ID not in result["matched_rule_ids"]


@pytest.mark.parametrize(
    "visual,expected,rule_id",
    [
        (
            {"visual_status": "visibly_healthy", "vigor": "high_vigor"},
            "Healthy Rice Leaf",
            "HRULE_003",
        ),
        (
            {
                "leaf_region": "leaf_tip",
                "zonation_present": True,
                "leaf_age": "mature_leaf",
            },
            "Leaf Scald",
            "EA_RULE_8C8A54B145",
        ),
        (
            {"lesion_shape": "oblong", "halo_color": "light_brown"},
            "Leaf Scald",
            "EA_RULE_CDDC7A936F",
        ),
        (
            {
                "lesion_shape": "narrow",
                "lesion_color": "brown",
                "lesion_width_mm": 1.0,
            },
            "Narrow Brown Leaf Spot",
            "EA_RULE_83353103A2",
        ),
    ],
)
def test_existing_valid_class_paths_remain_working(visual, expected, rule_id):
    result = _reason(visual)
    assert result["symbolic_prediction"] == expected
    assert rule_id in result["matched_rule_ids"]


def test_healthy_absence_and_contradiction_semantics_remain_working():
    supported = _reason(
        {
            "visual_status": "visibly_healthy",
            "other_observations": ["lacks spindle shaped lesions"],
        }
    )
    contradicted = _reason(
        {"visual_status": "visibly_healthy", "lesion_shape": "spindle_shaped"}
    )
    assert "HRULE_006" in supported["matched_rule_ids"]
    assert "HRULE_006" not in contradicted["matched_rule_ids"]
    assert _trace(contradicted, "HRULE_006")["match"]["condition_states"][0][
        "state"
    ] == CONDITION_CONTRADICTION


def test_unsafe_nbls_brown_leaf_blade_shortcut_remains_blocked():
    result = _reason({"lesion_color": "brown", "leaf_region": "leaf_blade"})
    assert "EA_RULE_D35B922621" not in result["matched_rule_ids"]
    assert result["symbolic_prediction"] == "Uncertain"
