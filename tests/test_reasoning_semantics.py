import pytest

from neuro_symbolic.artifact_loader import load_rules
from neuro_symbolic.reasoning_engine import (
    CONDITION_CONTRADICTION,
    CONDITION_MATCH,
    CONDITION_NOT_PROVIDED,
    OUTCOME_DIAGNOSTIC_CONTRADICTION,
    OUTCOME_DIFFERENTIAL,
    OUTCOME_REVIEW_REQUIRED,
    OUTCOME_SENESCENCE,
    OUTCOME_UNCERTAINTY,
    classify_rule_outcome,
    evaluate_rule,
    flatten_observations,
    reasoning_engine,
)


def _rule(rule_id):
    return next(rule for rule in load_rules() if rule["rule_id"] == rule_id)


def _observations(visual):
    return flatten_observations(
        {"visual_features": visual, "environment_context": {"enabled": False}}
    )


def _reason(visual):
    return reasoning_engine(
        {"visual_features": visual, "environment_context": {"enabled": False}},
        "research",
    )


def _trace(result, rule_id):
    return next(item for item in result["reasoning_trace"] if item["rule_id"] == rule_id)


def test_a_no_observations_abstains():
    result = _reason({})
    assert result["status"] == "insufficient_observation_evidence"
    assert result["symbolic_prediction"] == "Uncertain"
    assert result["symbolic_score"] == 0.0
    assert result["matched_rule_count"] == 0


def test_b_missing_mandatory_and_condition_does_not_fire():
    match = evaluate_rule(
        _rule("EA_RULE_EE3FB34441"),
        _observations({"leaf_region": "leaf_blade", "lesion_shape": "oval"}),
    )
    assert match["fired"] is False
    assert [item["state"] for item in match["condition_states"]] == [
        CONDITION_MATCH,
        CONDITION_MATCH,
        CONDITION_NOT_PROVIDED,
    ]


def test_c_all_mandatory_conditions_allow_rule_to_fire():
    match = evaluate_rule(
        _rule("EA_RULE_EE3FB34441"),
        _observations(
            {
                "leaf_region": "leaf_blade",
                "lesion_shape": "oval",
                "other_observations": ["necrotic"],
            }
        ),
    )
    assert match["fired"] is True
    assert all(
        item["state"] == CONDITION_MATCH for item in match["condition_states"]
    )
    assert match["score_eligible"] is False


def test_d_negation_contradiction_is_not_a_match():
    match = evaluate_rule(
        _rule("HRULE_006"),
        _observations(
            {"lesion_shape": "spindle_shaped", "visual_status": "visibly_healthy"}
        ),
    )
    assert match["fired"] is False
    assert match["condition_states"][0]["state"] == CONDITION_CONTRADICTION


def test_e_explicit_absence_can_match_negative_condition():
    match = evaluate_rule(
        _rule("HRULE_006"),
        _observations(
            {
                "visual_status": "visibly_healthy",
                "other_observations": ["lacks spindle shaped lesions"],
            }
        ),
    )
    assert match["fired"] is True
    assert match["condition_states"][0]["state"] == CONDITION_MATCH


def test_f_nbls_generic_brown_leaf_blade_false_positive_is_removed():
    result = _reason({"lesion_color": "brown", "leaf_region": "leaf_blade"})
    trace = _trace(result, "EA_RULE_D35B922621")
    assert trace["fired"] is False
    assert trace["match"]["condition_states"][0]["state"] == CONDITION_NOT_PROVIDED
    assert trace["match"]["condition_states"][0]["reason"] == (
        "CIRCULAR_OR_ETIOLOGICAL_PREREQUISITE"
    )
    assert "EA_RULE_D35B922621" not in result["matched_rule_ids"]
    assert result["symbolic_prediction"] == "Uncertain"


def test_g_generic_spindle_does_not_satisfy_circular_leaf_blast_condition():
    result = _reason({"lesion_shape": "spindle_shaped"})
    trace = _trace(result, "EA_RULE_9EDFE97BF1")
    assert trace["fired"] is False
    assert trace["match"]["condition_states"][0]["state"] == CONDITION_NOT_PROVIDED
    assert trace["match"]["condition_states"][0]["reason"] == (
        "CIRCULAR_OR_ETIOLOGICAL_PREREQUISITE"
    )


def test_h_conclusion_is_not_required_as_observation():
    result = _reason({"lesion_shape": "oblong", "halo_color": "light_brown"})
    trace = _trace(result, "EA_RULE_CDDC7A936F")
    assert trace["fired"] is True
    assert trace["match"]["conclusion_used_for_firing"] is False
    assert trace["match"]["conclusion_score"] == 0.0
    assert "EA_RULE_CDDC7A936F" in result["matched_rule_ids"]


def test_i_healthy_spindle_contradiction_does_not_support_healthy():
    result = _reason(
        {"visual_status": "visibly_healthy", "lesion_shape": "spindle_shaped"}
    )
    trace = _trace(result, "HRULE_006")
    assert trace["match"]["condition_states"][0]["state"] == (
        CONDITION_CONTRADICTION
    )
    assert "HRULE_006" not in result["matched_rule_ids"]
    assert result["disease_scores"]["Healthy Rice Leaf"] == 0.0


@pytest.mark.parametrize(
    "rule_id,outcome",
    [
        ("HRULE_004", OUTCOME_DIAGNOSTIC_CONTRADICTION),
        ("HRULE_009", OUTCOME_SENESCENCE),
        ("HRULE_012", OUTCOME_REVIEW_REQUIRED),
        ("HRULE_011", OUTCOME_UNCERTAINTY),
        ("EA_RULE_E2B3F55F7E", OUTCOME_DIFFERENTIAL),
    ],
)
def test_j_non_diagnostic_outcomes_are_not_positive_support(rule_id, outcome):
    rule = _rule(rule_id)
    assert classify_rule_outcome(rule) == outcome
    condition_observations = [
        condition["raw_text"] for condition in rule.get("conditions", [])
    ]
    match = evaluate_rule(
        rule,
        _observations({"other_observations": condition_observations}),
    )
    assert match["fired"] is True
    assert match["score_eligible"] is False


@pytest.mark.parametrize(
    "visual,rule_id",
    [
        (
            {
                "leaf_region": "leaf_tip",
                "zonation_present": True,
                "leaf_age": "mature_leaf",
            },
            "EA_RULE_8C8A54B145",
        ),
        (
            {"lesion_shape": "oblong", "halo_color": "light_brown"},
            "EA_RULE_CDDC7A936F",
        ),
    ],
)
def test_k_valid_leaf_scald_paths_are_preserved(visual, rule_id):
    result = _reason(visual)
    trace = _trace(result, rule_id)
    assert trace["fired"] is True
    assert trace["score_eligible"] is True
    assert rule_id in result["matched_rule_ids"]
    assert result["symbolic_prediction"] == "Leaf Scald"


def test_existing_nbls_full_and_rule_fires_without_conclusion_input():
    result = _reason(
        {
            "lesion_shape": "narrow",
            "lesion_color": "brown",
            "lesion_width_mm": 1.0,
        }
    )
    trace = _trace(result, "EA_RULE_83353103A2")
    assert trace["fired"] is True
    assert trace["score_eligible"] is True
    assert result["symbolic_prediction"] == "Narrow Brown Leaf Spot"
