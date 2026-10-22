import asyncio
import importlib
import sys
from io import BytesIO
from types import ModuleType

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile


def _upload(content=b"image"):
    return UploadFile(
        file=BytesIO(content),
        filename="leaf.png",
        headers=Headers({"content-type": "image/png"}),
    )


def _load_main(monkeypatch):
    predictor_stub = ModuleType("predictor")
    predictor_stub.predict_with_gradcam = lambda *_args, **_kwargs: {}
    monkeypatch.setitem(sys.modules, "predictor", predictor_stub)
    sys.modules.pop("main", None)
    return importlib.import_module("main")


def test_invalid_observation_unknown_field_returns_422(monkeypatch):
    main = _load_main(monkeypatch)
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            main.predict(
                _upload(),
                observations_json='{"made_up_feature": "x"}',
                runtime_mode=None,
                include_visualizations=True,
            )
        )
    assert error.value.status_code == 422


def test_upload_size_limit_is_preserved(monkeypatch):
    main = _load_main(monkeypatch)
    monkeypatch.setattr(main, "MAX_UPLOAD_SIZE_BYTES", 4)
    with pytest.raises(HTTPException) as error:
        asyncio.run(main.predict(_upload(b"12345")))
    assert error.value.status_code == 413


def test_non_image_upload_is_rejected(monkeypatch):
    main = _load_main(monkeypatch)
    upload = UploadFile(
        file=BytesIO(b"text"),
        filename="notes.txt",
        headers=Headers({"content-type": "text/plain"}),
    )
    with pytest.raises(HTTPException) as error:
        asyncio.run(main.predict(upload))
    assert error.value.status_code == 400


def test_api_v2_serialization_preserves_legacy_fields(monkeypatch):
    main = _load_main(monkeypatch)
    fake = {
        "api_version": "2.0.0",
        "runtime_mode": "research",
        "artifact_versions": {"rules": {"version": "1.0.0"}},
        "cnn_result": {"prediction": "leaf_blast", "confidence": 0.91},
        "observation_result": {"input_mode": "image_only"},
        "visual_evidence": {
            "attention_coverage_percent": 8.5,
            "segmentation_validated": False,
        },
        "safety_result": {"requires_manual_review": False},
        "symbolic_result": {
            "status": "insufficient_observation_evidence",
            "matched_rule_count": 0,
        },
        "fusion_result": {
            "final_prediction": "leaf_blast",
            "display_name": "Leaf Blast",
            "candidate_prediction": "leaf_blast",
            "candidate_display_name": "Leaf Blast",
            "final_confidence": 0.91,
            "requires_manual_review": False,
        },
        "management_result": {"actionable": False},
        "explanation": {"summary": "Test"},
        "top_label": "leaf_blast",
        "top_conf": 0.91,
        "second_label": "brown_spot",
        "second_conf": 0.04,
        "all_predictions": {
            "brown_spot": 0.04,
            "healthy": 0.02,
            "leaf_blast": 0.91,
            "leaf_scald": 0.02,
            "narrow_brown_spot": 0.01,
        },
        "infected_percent": 8.5,
        "attention_coverage_percent": 8.5,
        "final_decision": "leaf_blast",
        "trust_level": "high",
        "severity": "moderate",
        "recommendation": "Retake or consult.",
        "warning": "Advisory.",
        "reasoning_notes": ["Image-only symbolic abstention."],
        "phenotype_facts": [],
        "knowledge_sources": [],
        "matched_rules": [],
        "conflicts_detected": [],
        "selected_rule": None,
        "conflict_resolution_note": "CNN-led after abstention.",
        "ambiguity_detected": False,
        "contradiction_detected": False,
        "gradcam_heatmap_base64": "aGVhdA==",
        "gradcam_overlay_base64": "b3Zlcg==",
        "attention_threshold_map_base64": "bWFw",
        "lesion_mask_base64": "bWFw",
    }
    main.predict_with_gradcam = lambda *_args, **_kwargs: fake
    response = asyncio.run(main.predict(_upload()))
    payload = response.model_dump(by_alias=True)
    assert payload["api_version"] == "2.0.0"
    assert payload["fusion_result"]["final_prediction"] == "leaf_blast"
    assert payload["fusion_result"]["candidate_prediction"] == "leaf_blast"
    assert payload["fusion_result"]["requires_manual_review"] is False
    assert payload["symbolic_result"]["matched_rule_count"] == 0
    assert payload["visual_evidence"]["segmentation_validated"] is False
    assert payload["class"] == "leaf_blast"
    assert payload["confidence"] == 0.91
    assert payload["lesion_mask_base64"] == payload[
        "attention_threshold_map_base64"
    ]


def test_invalid_image_from_predictor_is_400(monkeypatch):
    main = _load_main(monkeypatch)

    def invalid(*_args, **_kwargs):
        from PIL import UnidentifiedImageError

        raise UnidentifiedImageError("not an image")

    main.predict_with_gradcam = invalid
    with pytest.raises(HTTPException) as error:
        asyncio.run(main.predict(_upload(b"not an image")))
    assert error.value.status_code == 400


def test_runtime_mode_escalation_returns_403(monkeypatch):
    monkeypatch.setenv("NS_RUNTIME_MODE", "production")
    main = _load_main(monkeypatch)
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            main.predict(
                _upload(),
                observations_json=None,
                runtime_mode="research",
                include_visualizations=True,
            )
        )
    assert error.value.status_code == 403
    assert "exceeds the server" in error.value.detail


def test_health_and_system_info_report_server_mode(monkeypatch, tmp_path):
    monkeypatch.setenv("NS_RUNTIME_MODE", "staging")
    main = _load_main(monkeypatch)
    # The predictor is mocked by _load_main; use a local checksum fixture too.
    model_file = tmp_path / "model-fixture.keras"
    model_file.write_bytes(b"system-info-checksum-fixture")
    monkeypatch.setattr(main, "MODEL_PATH", model_file)
    assert main.health()["runtime_mode"] == "staging"
    assert main.system_info()["runtime_mode"] == "staging"


def test_production_guided_policy_error_serializes_as_403(monkeypatch):
    monkeypatch.setenv("NS_RUNTIME_MODE", "production")
    main = _load_main(monkeypatch)
    from neuro_symbolic.observation import GuidedObservationPolicyError

    def rejected(*_args, **_kwargs):
        raise GuidedObservationPolicyError(
            "Guided free-text symbolic execution is disabled by server policy."
        )

    main.predict_with_gradcam = rejected
    with pytest.raises(HTTPException) as error:
        asyncio.run(
            main.predict(
                _upload(),
                observations_json='{"vigor":"user supplied"}',
                runtime_mode="production",
                include_visualizations=True,
            )
        )
    assert error.value.status_code == 403
    assert "disabled by server policy" in error.value.detail


def test_safety_withholding_serializes_null_final_and_legacy_uncertain(monkeypatch):
    monkeypatch.setenv("NS_RUNTIME_MODE", "research")
    main = _load_main(monkeypatch)
    from neuro_symbolic.orchestrator import orchestrate_diagnosis

    probabilities = {
        "brown_spot": 0.20,
        "healthy": 0.10,
        "leaf_blast": 0.55,
        "leaf_scald": 0.08,
        "narrow_brown_spot": 0.07,
    }
    v2 = orchestrate_diagnosis(
        cnn_probabilities=probabilities,
        top_label="leaf_blast",
        top_confidence=0.55,
        second_label="brown_spot",
        second_confidence=0.20,
        attention_coverage_percent=5.0,
        severity_heuristic="moderate",
        runtime_mode="research",
        sample_id="api-safety-test",
    )
    output = {
        **v2,
        "top_label": "leaf_blast",
        "top_conf": 0.55,
        "second_label": "brown_spot",
        "second_conf": 0.20,
        "all_predictions": probabilities,
        "infected_percent": 5.0,
        "attention_coverage_percent": 5.0,
        "final_decision": "uncertain",
        "trust_level": "low",
        "severity": "moderate",
        "recommendation": "Retake or consult.",
        "warning": "Manual review required.",
        "reasoning_notes": [v2["explanation"]["summary"]],
        "phenotype_facts": [],
        "knowledge_sources": [],
        "matched_rules": [],
        "conflicts_detected": [],
        "selected_rule": None,
        "conflict_resolution_note": v2["fusion_result"]["resolution"],
        "ambiguity_detected": False,
        "contradiction_detected": False,
        "gradcam_heatmap_base64": "aGVhdA==",
        "gradcam_overlay_base64": "b3Zlcg==",
        "attention_threshold_map_base64": "bWFw",
        "lesion_mask_base64": "bWFw",
    }
    main.predict_with_gradcam = lambda *_args, **_kwargs: output
    payload = asyncio.run(main.predict(_upload())).model_dump(by_alias=True)
    assert payload["fusion_result"]["final_prediction"] is None
    assert payload["fusion_result"]["display_name"] == "Uncertain"
    assert payload["fusion_result"]["candidate_prediction"] == "leaf_blast"
    assert payload["fusion_result"]["requires_manual_review"] is True
    assert payload["class"] == "leaf_blast"
    assert payload["final_decision"] == "uncertain"
