import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from conflict_resolution.conflict_resolver import resolve_management_rules
from neuro_symbolic.artifact_loader import (
    RuntimeModeEscalationError,
    get_runtime_mode,
    load_rules,
)
from neuro_symbolic.diagnostic_conflict_resolver import (
    resolve_diagnostic_conflict,
)
from neuro_symbolic.observation import (
    GuidedObservationPolicyError,
    observation_schema_response,
)
from neuro_symbolic.orchestrator import orchestrate_diagnosis
from neuro_symbolic.reasoning_engine import rule_allowed_in_mode
from neuro_symbolic.schemas import GuidedObservations


ROOT = Path(__file__).resolve().parent.parent
MODEL_HASH_BEFORE = (
    "3F91DA161D761F0DA3BC4C157115F44F1A8CD25B3DF624BD2B79AD77A6FC7A94"
)
CNN = {
    "brown_spot": 0.03,
    "healthy": 0.02,
    "leaf_blast": 0.90,
    "leaf_scald": 0.02,
    "narrow_brown_spot": 0.03,
}


def _orchestrate(
    guided=None,
    *,
    runtime_mode="research",
    probabilities=None,
    top_confidence=0.90,
    second_confidence=0.03,
):
    values = probabilities or CNN
    return orchestrate_diagnosis(
        cnn_probabilities=values,
        top_label="leaf_blast",
        top_confidence=top_confidence,
        second_label="brown_spot",
        second_confidence=second_confidence,
        attention_coverage_percent=5.0,
        severity_heuristic="moderate",
        guided_observations=guided,
        runtime_mode=runtime_mode,
        sample_id="integration-test",
    )


def test_model_hash_unchanged():
    model_path = ROOT / "models" / "rice_model_fixed.keras"
    if not model_path.is_file():
        pytest.skip(
            "Trained model is intentionally excluded from this audit package."
        )
    actual = hashlib.sha256(model_path.read_bytes()).hexdigest().upper()
    assert actual == MODEL_HASH_BEFORE


def test_image_only_does_not_fabricate_observations():
    result = _orchestrate()
    observation = result["observation_result"]
    assert observation["input_mode"] == "image_only"
    assert observation["provided_observations"] == {}
    assert observation["normalized_observations"] == {}
    assert "lesion_shape" in observation["missing_required_or_relevant_features"]


def test_image_only_symbolic_abstains_and_has_zero_reliability():
    result = _orchestrate()
    assert result["symbolic_result"]["status"] == "insufficient_observation_evidence"
    assert result["symbolic_result"]["matched_rule_ids"] == []
    assert result["symbolic_result"]["reliability"] == 0.0
    assert result["fusion_result"]["agreement_status"] == "symbolic_abstention"
    assert result["fusion_result"]["cnn_weight"] == 1.0
    assert result["fusion_result"]["symbolic_weight"] == 0.0
    assert result["fusion_result"]["raw_phase7_cnn_weight"] == 0.9
    assert result["fusion_result"]["raw_phase7_symbolic_weight"] == 0.1
    assert result["fusion_result"]["abstention_policy_applied"] is True
    assert result["fusion_result"]["class_scores"] == CNN
    assert "no effective contribution" in result["explanation"][
        "why_symbolic_contributed"
    ]


def test_guided_observations_are_user_confirmed_and_can_match():
    guided = GuidedObservations(
        lesion_present=True,
        lesion_shape="oblong",
        halo_color="light_brown",
    )
    result = _orchestrate(guided)
    assert result["observation_result"]["input_mode"] == "guided_phenotype"
    assert set(result["observation_result"]["observation_sources"].values()) == {
        "user_confirmed"
    }
    assert result["symbolic_result"]["matched_rule_count"] > 0
    assert "EA_RULE_CDDC7A936F" in result["symbolic_result"]["matched_rule_ids"]
    assert result["fusion_result"]["abstention_policy_applied"] is False
    assert result["fusion_result"]["cnn_weight"] == result["fusion_result"][
        "raw_phase7_cnn_weight"
    ]
    assert result["explanation"]["provided_observed_features"]
    assert result["explanation"]["matched_observed_features"]


def test_empty_guided_object_behaves_as_image_only():
    result = _orchestrate(GuidedObservations())
    assert result["observation_result"]["input_mode"] == "image_only"
    assert result["observation_result"]["provided_observations"] == {}
    assert result["observation_result"]["observation_sources"] == {}
    assert result["observation_result"]["provided_observed_features"] == []


def test_default_empty_other_observations_is_not_user_confirmed():
    result = _orchestrate(GuidedObservations(lesion_shape="oval"))
    provided = result["observation_result"]["provided_observations"]
    assert provided == {"lesion_shape": "oval"}
    assert "other_observations" not in result["observation_result"][
        "observation_sources"
    ]


def test_valid_graph_value_is_provided_but_not_falsely_matched():
    result = _orchestrate(GuidedObservations(lesion_shape="diamond_shaped"))
    assert result["symbolic_result"]["matched_rule_count"] == 0
    provided = result["explanation"]["provided_observed_features"][0]
    assert provided["field"] == "lesion_shape"
    assert provided["submitted_value"] == "diamond_shaped"
    assert provided["normalized_value"] == "diamond_shaped"
    assert provided["source"] == "user_confirmed"
    assert provided["enum_validated"] is True
    assert result["explanation"]["matched_observed_features"] == []


@pytest.mark.parametrize("server_mode", ["production", "staging", "research"])
@pytest.mark.parametrize("request_mode", ["production", "staging", "research"])
def test_server_runtime_mode_is_authoritative(monkeypatch, server_mode, request_mode):
    rank = {"production": 0, "staging": 1, "research": 2}
    monkeypatch.setenv("NS_RUNTIME_MODE", server_mode)
    if rank[request_mode] <= rank[server_mode]:
        assert get_runtime_mode(request_mode) == request_mode
    else:
        with pytest.raises(RuntimeModeEscalationError):
            get_runtime_mode(request_mode)


def test_production_rejects_guided_free_text_by_default(monkeypatch):
    monkeypatch.setenv("NS_RUNTIME_MODE", "production")
    monkeypatch.delenv("ALLOW_UNVALIDATED_GUIDED_OBSERVATIONS", raising=False)
    with pytest.raises(GuidedObservationPolicyError):
        _orchestrate(
            GuidedObservations(dryness="user supplied"), runtime_mode="production"
        )


def test_production_guided_free_text_requires_explicit_server_override(monkeypatch):
    monkeypatch.setenv("NS_RUNTIME_MODE", "production")
    monkeypatch.setenv("ALLOW_UNVALIDATED_GUIDED_OBSERVATIONS", "true")
    result = _orchestrate(
        GuidedObservations(dryness="user supplied"), runtime_mode="production"
    )
    assert result["runtime_mode"] == "production"
    assert result["observation_result"]["categorical_values_enum_validated"] is False
    assert any(
        "explicit server policy" in warning
        for warning in result["observation_result"]["warnings"]
    )


def test_research_guided_free_text_is_warned(monkeypatch):
    monkeypatch.setenv("NS_RUNTIME_MODE", "research")
    result = _orchestrate(
        GuidedObservations(dryness="user supplied"), runtime_mode="research"
    )
    assert any(
        "research mode" in warning
        for warning in result["observation_result"]["warnings"]
    )


def test_staging_guided_free_text_uses_server_policy(monkeypatch):
    monkeypatch.setenv("NS_RUNTIME_MODE", "staging")
    monkeypatch.delenv("ALLOW_UNVALIDATED_GUIDED_OBSERVATIONS", raising=False)
    with pytest.raises(GuidedObservationPolicyError):
        _orchestrate(
            GuidedObservations(dryness="user supplied"), runtime_mode="staging"
        )


def test_guided_observations_reject_unknown_fields():
    with pytest.raises(ValidationError):
        GuidedObservations.model_validate({"invented_feature": "value"})


def test_observation_schema_reports_provenance_backed_categorical_vocabulary():
    schema = observation_schema_response()
    assert schema["fields"]["lesion_shape"]["allowed_values"]
    assert schema["fields"]["lesion_shape"]["categorical_values_available"] is True
    assert "string" in schema["fields"]["lesion_shape"]["input_types"]
    assert schema["fields"]["lesion_distribution"]["allowed_values"] is None


@pytest.mark.parametrize(
    "state,production,staging,research",
    [
        ("ACTIVE_CANDIDATE", True, True, True),
        ("STAGING_CANDIDATE", False, True, True),
        ("EVIDENCE_SUPPORTED_HOLD", False, False, True),
        ("HOLD_PARSE_INCOMPLETE", False, False, False),
    ],
)
def test_rule_runtime_state_gating(state, production, staging, research):
    rule = {"runtime_state": state}
    assert rule_allowed_in_mode(rule, "production") is production
    assert rule_allowed_in_mode(rule, "staging") is staging
    assert rule_allowed_in_mode(rule, "research") is research


def test_phase5_metadata_is_preserved_on_loaded_rules():
    rule = next(item for item in load_rules() if item["conditions"])
    assert "validation" in rule
    assert "provenance" in rule
    assert "runtime_state" in rule
    assert "original_extracted_value" in rule["provenance"]


def test_management_resolution_is_separate_and_gated():
    result = resolve_management_rules(
        final_class="leaf_blast",
        runtime_mode="research",
        safety_safeguards=[],
    )
    assert result["actionable"] is False
    assert result["advisory_only"] is True
    assert result["recommendation"].startswith("Retake")


def test_gradcam_metadata_never_claims_segmentation():
    result = _orchestrate()
    assert result["visual_evidence"]["segmentation_validated"] is False
    assert "not validated lesion segmentation" in result["visual_evidence"][
        "disclaimer"
    ]


def test_safety_can_force_diagnostic_uncertainty():
    fusion = {
        "fusion": {"final_prediction": "Leaf Blast", "final_confidence": 0.8},
        "conflict": {"detected": False, "resolution": "Agreement."},
    }
    symbolic = {"status": "completed"}
    safety = {"force_uncertainty": True, "requires_manual_review": True}
    result = resolve_diagnostic_conflict(fusion, symbolic, safety)
    assert result["status"] == "safety_forced_uncertainty"
    assert result["final_prediction"] is None


def test_orchestrator_withholds_authoritative_final_but_keeps_candidate():
    probabilities = {
        "brown_spot": 0.20,
        "healthy": 0.10,
        "leaf_blast": 0.55,
        "leaf_scald": 0.08,
        "narrow_brown_spot": 0.07,
    }
    result = _orchestrate(
        probabilities=probabilities,
        top_confidence=0.55,
        second_confidence=0.20,
    )
    fusion = result["fusion_result"]
    assert fusion["final_prediction"] is None
    assert fusion["display_name"] == "Uncertain"
    assert fusion["candidate_prediction"] == "leaf_blast"
    assert fusion["candidate_display_name"] == "Leaf Blast"
    assert fusion["requires_manual_review"] is True
    assert result["explanation"]["summary"].startswith(
        "Diagnosis withheld because deterministic safety safeguards"
    )


def test_normal_orchestrator_result_publishes_authoritative_final():
    result = _orchestrate()
    assert result["fusion_result"]["final_prediction"] == "leaf_blast"
    assert result["fusion_result"]["candidate_prediction"] == "leaf_blast"
    assert result["explanation"]["summary"].startswith("Final diagnosis: Leaf Blast")


def test_runtime_artifacts_match_their_hash_manifest():
    manifest = json.loads(
        (ROOT / "research_artifacts/runtime_v1/artifact_manifest_v1.json").read_text(
            encoding="utf-8"
        )
    )
    for record in manifest["artifacts"]:
        runtime = ROOT / record["runtime_relative_path"]
        assert hashlib.sha256(runtime.read_bytes()).hexdigest().upper() == record[
            "sha256"
        ]
