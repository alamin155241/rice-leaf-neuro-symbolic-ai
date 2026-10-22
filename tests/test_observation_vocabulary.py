import asyncio
import hashlib
import importlib
import json
import sys
from io import BytesIO
from pathlib import Path
from types import ModuleType

import pytest
from fastapi import HTTPException
from jsonschema import Draft202012Validator
from starlette.datastructures import Headers, UploadFile

from neuro_symbolic.artifact_loader import validate_runtime_artifacts
from neuro_symbolic.observation import GuidedObservationPolicyError
from neuro_symbolic.observation import observation_schema_response
from neuro_symbolic.observation_vocabulary import (
    ObservationVocabularyValidationError,
    load_observation_vocabulary,
    validate_observations,
)
from neuro_symbolic.orchestrator import orchestrate_diagnosis
from neuro_symbolic.schemas import GuidedObservations


ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_ROOT = ROOT / "research_artifacts" / "runtime_v1"
EXPECTED_CANONICAL_VALUES = {
    "lesion_shape": {
        "spindle_shaped",
        "diamond_shaped",
        "oval",
        "oblong",
        "elongated",
        "narrow",
    },
    "lesion_color": {"brown", "light_brown"},
    "lesion_center_color": {"gray", "white"},
    "lesion_margin_color": {"brown"},
    "lesion_size": {"pin_head_size"},
    "leaf_region": {"leaf_blade", "leaf_tip", "leaf_edge"},
    "halo_color": {"light_brown", "yellow"},
    "yellowing": {"yellowing"},
    "visual_status": {"visibly_healthy"},
    "vigor": {"high_vigor"},
    "leaf_age": {"mature_leaf", "older_lower_leaves"},
    "growth_stage": {
        "seedling",
        "early_tillering_stages",
        "boot_to_heading",
        "late_tillering_stage",
        "vegetative_lag_phase",
    },
}
CNN = {
    "brown_spot": 0.03,
    "healthy": 0.02,
    "leaf_blast": 0.90,
    "leaf_scald": 0.02,
    "narrow_brown_spot": 0.03,
}


def _orchestrate(guided=None, mode="research"):
    return orchestrate_diagnosis(
        cnn_probabilities=CNN,
        top_label="leaf_blast",
        top_confidence=0.90,
        second_label="brown_spot",
        second_confidence=0.03,
        attention_coverage_percent=5.0,
        severity_heuristic="moderate",
        guided_observations=guided,
        runtime_mode=mode,
        sample_id="vocabulary-test",
    )


def test_vocabulary_artifact_matches_json_schema():
    vocabulary = json.loads(
        (ARTIFACT_ROOT / "observation_vocabulary_v1.json").read_text(
            encoding="utf-8"
        )
    )
    schema = json.loads(
        (ARTIFACT_ROOT / "observation_vocabulary_schema_v1.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator(schema).validate(vocabulary)


def test_vocabulary_manifest_hash_is_validated():
    hashes = validate_runtime_artifacts()
    assert hashes["observation_vocabulary"] == hashlib.sha256(
        (ARTIFACT_ROOT / "observation_vocabulary_v1.json").read_bytes()
    ).hexdigest().upper()


def test_closed_expected_set_prevents_unsupported_invented_values():
    vocabulary = load_observation_vocabulary()
    actual = {
        field_name: {
            item["canonical_value"] for item in field["allowed_values"]
        }
        for field_name, field in vocabulary["fields"].items()
        if field["categorical_values_available"]
    }
    assert actual == EXPECTED_CANONICAL_VALUES
    assert vocabulary["generation_policy"]["invented_values_allowed"] is False
    assert vocabulary["generation_policy"]["semantic_guessing_allowed"] is False


def test_every_categorical_value_has_provenance():
    for field in load_observation_vocabulary()["fields"].values():
        for value in field.get("allowed_values") or []:
            provenance = value["provenance"]
            assert provenance["source_ids"]
            assert provenance["source_texts"]
            assert provenance["source_artifacts"]


def test_exact_values_and_aliases_are_deduplicated_per_field():
    for field in load_observation_vocabulary()["fields"].values():
        values = field.get("allowed_values") or []
        canonicals = [item["canonical_value"] for item in values]
        assert len(canonicals) == len(set(canonicals))
        accepted: dict[str, str] = {}
        for item in values:
            candidates = [
                item["canonical_value"],
                *item["original_values"],
                *[alias["value"] for alias in item["aliases"]],
            ]
            for candidate in candidates:
                key = candidate.strip().casefold()
                assert accepted.get(key, item["canonical_value"]) == item[
                    "canonical_value"
                ]
                accepted[key] = item["canonical_value"]


def test_uncertain_similar_values_are_not_semantically_merged():
    shape = EXPECTED_CANONICAL_VALUES["lesion_shape"]
    assert {"spindle_shaped", "diamond_shaped", "oval"} <= shape
    assert "elliptical" not in {
        alias["value"]
        for value in load_observation_vocabulary()["fields"]["lesion_shape"][
            "allowed_values"
        ]
        for alias in value["aliases"]
        if value["canonical_value"] in {"spindle_shaped", "diamond_shaped"}
    }
    assert {"brown", "light_brown"} == (
        EXPECTED_CANONICAL_VALUES["lesion_color"]
    )


def test_necrosis_is_a_boolean_state_and_not_a_lesion_color():
    vocabulary = load_observation_vocabulary()
    necrosis = vocabulary["fields"]["necrosis_present"]
    lesion_colors = {
        item["canonical_value"]
        for item in vocabulary["fields"]["lesion_color"]["allowed_values"]
    }
    assert necrosis["input_types"] == ["boolean"]
    assert necrosis["boolean_allowed_values"] == [True, False]
    assert "necrotic" not in lesion_colors
    with pytest.raises(ObservationVocabularyValidationError):
        validate_observations({"lesion_color": "necrotic"})
    normalized, records, unvalidated = validate_observations(
        {"necrosis_present": False}
    )
    assert normalized == {"necrosis_present": False}
    assert records[0]["validation_type"] == "schema_defined_boolean"
    assert unvalidated == []


def test_explicit_alias_normalizes_and_retains_alias_provenance():
    normalized, records, unvalidated = validate_observations(
        {"lesion_center_color": "greyish"}
    )
    assert normalized == {"lesion_center_color": "gray"}
    assert unvalidated == []
    assert records[0]["enum_validated"] is True
    assert records[0]["normalization"]["input_kind"] == "explicit_alias"
    assert records[0]["normalization"]["matched_alias"]["source"] == (
        "explicit_normalization_alias"
    )


def test_unsupported_alias_is_rejected_with_safe_canonical_list():
    with pytest.raises(ObservationVocabularyValidationError) as error:
        validate_observations({"lesion_shape": "elliptical spindle"})
    assert error.value.field == "lesion_shape"
    assert "spindle_shaped" in error.value.allowed_values
    assert "elliptical spindle" not in error.value.allowed_values


def test_categorical_validation_error_is_http_422(monkeypatch):
    predictor_stub = ModuleType("predictor")
    predictor_stub.predict_with_gradcam = lambda *_args, **_kwargs: {}
    monkeypatch.setitem(sys.modules, "predictor", predictor_stub)
    sys.modules.pop("main", None)
    main = importlib.import_module("main")

    def validate_then_stop(*_args, **kwargs):
        guided = kwargs["guided_observations"]
        validate_observations(guided.model_dump(exclude_none=True))
        raise AssertionError("Invalid vocabulary value should stop first.")

    main.predict_with_gradcam = validate_then_stop
    upload = UploadFile(
        file=BytesIO(b"image"),
        filename="leaf.png",
        headers=Headers({"content-type": "image/png"}),
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            main.predict(
                upload,
                observations_json='{"lesion_shape":"ellipse-like"}',
                runtime_mode="research",
                include_visualizations=False,
            )
        )
    assert error.value.status_code == 422
    assert error.value.detail["field"] == "lesion_shape"
    assert error.value.detail["allowed_values"] == [
        "spindle_shaped",
        "diamond_shaped",
        "oval",
        "oblong",
        "elongated",
        "narrow",
    ]


def test_boolean_fields_are_schema_validated_without_scientific_enum_claim():
    normalized, records, unvalidated = validate_observations(
        {"lesion_present": True, "coalescence": False}
    )
    assert normalized == {"lesion_present": True, "coalescence": False}
    assert unvalidated == []
    assert {item["validation_type"] for item in records} == {
        "schema_defined_boolean"
    }


def test_numeric_field_has_no_invented_range():
    field = load_observation_vocabulary()["fields"]["lesion_width_mm"]
    assert field["allowed_values"] is None
    assert field["numeric_constraints"] is None
    guided = GuidedObservations(lesion_width_mm=-0.5)
    normalized, records, unvalidated = validate_observations(
        guided.model_dump(exclude_none=True, exclude_defaults=True)
    )
    assert normalized["lesion_width_mm"] == -0.5
    assert records[0]["validation_type"] == "schema_defined_number"
    assert unvalidated == []


def test_mixed_type_boolean_categorical_and_free_text_behavior():
    normalized, records, unvalidated = validate_observations(
        {"yellowing": True, "dryness": "crispy"}
    )
    assert normalized == {"yellowing": True, "dryness": "crispy"}
    assert records[0]["validation_type"] == "schema_defined_boolean"
    assert unvalidated == ["dryness"]
    normalized, records, unvalidated = validate_observations(
        {"yellowing": "Yellowing"}
    )
    assert normalized == {"yellowing": "yellowing"}
    assert records[0]["enum_validated"] is True
    assert unvalidated == []


def test_research_mode_allows_and_warns_on_no_vocabulary_free_text():
    result = _orchestrate(GuidedObservations(dryness="user observed"))
    observation = result["observation_result"]
    assert observation["unvalidated_fields"] == ["dryness"]
    assert observation["observation_validation"][0]["enum_validated"] is False
    assert any("research mode" in warning for warning in observation["warnings"])


def test_staging_and_production_block_unvalidated_text_by_default(monkeypatch):
    monkeypatch.delenv("ALLOW_UNVALIDATED_GUIDED_OBSERVATIONS", raising=False)
    for mode in ("staging", "production"):
        monkeypatch.setenv("NS_RUNTIME_MODE", mode)
        with pytest.raises(GuidedObservationPolicyError):
            _orchestrate(GuidedObservations(dryness="user observed"), mode)


def test_production_explicit_override_allows_unvalidated_text(monkeypatch):
    monkeypatch.setenv("NS_RUNTIME_MODE", "production")
    monkeypatch.setenv("ALLOW_UNVALIDATED_GUIDED_OBSERVATIONS", "true")
    result = _orchestrate(
        GuidedObservations(dryness="user observed"), "production"
    )
    assert result["observation_result"]["unvalidated_fields"] == ["dryness"]
    assert any(
        "explicit server policy" in warning
        for warning in result["observation_result"]["warnings"]
    )


def test_observation_schema_response_contains_full_safe_vocabulary():
    response = observation_schema_response()
    shape = response["fields"]["lesion_shape"]
    assert response["version"] == "1.2.0"
    assert shape["categorical_values_available"] is True
    assert shape["allowed_values"][0]["display_name"]
    assert shape["allowed_values"][0]["provenance"]["source_ids"]
    assert response["fields"]["lesion_distribution"]["allowed_values"] is None
    assert response["fields"]["lesion_present"][
        "boolean_allowed_values"
    ] == [True, False]
    assert response["fields"]["necrosis_present"][
        "boolean_allowed_values"
    ] == [True, False]
    assert not any(
        str(ROOT).casefold() in json.dumps(field).casefold()
        for field in response["fields"].values()
    )


def test_submitted_and_normalized_values_are_both_preserved_in_trace():
    result = _orchestrate(GuidedObservations(lesion_center_color="greyish"))
    record = result["observation_result"]["observation_validation"][0]
    assert record["submitted_value"] == "greyish"
    assert record["normalized_value"] == "gray"
    assert record["source"] == "user_confirmed"
    trace = result["symbolic_result"]["reasoning_trace"]
    assert trace[0]["event"] == "observation_vocabulary_validation"
    assert trace[0]["fields"][0]["normalized_value"] == "gray"
    assert all("condition_text" in item for item in trace[1:])


def test_valid_vocabulary_observations_can_drive_existing_phase6_rule():
    result = _orchestrate(
        GuidedObservations(
            visual_status="visibly_healthy",
            vigor="high_vigor",
        )
    )
    assert "HRULE_003" in result["symbolic_result"]["matched_rule_ids"]


def test_vocabulary_value_without_matching_condition_is_not_falsely_matched():
    result = _orchestrate(GuidedObservations(lesion_shape="diamond_shaped"))
    observation = result["observation_result"]["observation_validation"][0]
    assert observation["enum_validated"] is True
    assert result["symbolic_result"]["matched_rule_ids"] == []


def test_model_hash_is_unchanged_by_vocabulary_extension():
    path = ROOT / "models" / "rice_model_fixed.keras"
    if not path.is_file():
        pytest.skip("Model is intentionally absent from this package.")
    assert hashlib.sha256(path.read_bytes()).hexdigest().upper() == (
        "3F91DA161D761F0DA3BC4C157115F44F1A8CD25B3DF624BD2B79AD77A6FC7A94"
    )
