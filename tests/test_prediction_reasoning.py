import asyncio
from io import BytesIO
import importlib
import sys
from types import ModuleType

from starlette.datastructures import Headers, UploadFile


def _fake_prediction() -> dict:
    return {
        "top_label": "leaf_blast",
        "top_conf": 0.91,
        "second_label": "brown_spot",
        "second_conf": 0.04,
        "all_predictions": {
            "leaf_blast": 0.91,
            "brown_spot": 0.04,
            "healthy": 0.03,
            "leaf_scald": 0.01,
            "narrow_brown_spot": 0.01,
        },
        "infected_percent": 8.5,
        "attention_coverage_percent": 8.5,
        "final_decision": "leaf_blast",
        "trust_level": "high",
        "severity": "moderate",
        "recommendation": "Inspect additional leaves.",
        "warning": "Pending expert validation.",
        "reasoning_notes": ["Top prediction accepted: leaf_blast."],
        "phenotype_facts": ["Lesion pattern: spindle-shaped lesion"],
        "knowledge_sources": ["draft source [pending_expert_validation]"],
        "matched_rules": [{"rule_id": "TEST_RULE"}],
        "conflicts_detected": [],
        "selected_rule": {"rule_id": "TEST_RULE"},
        "conflict_resolution_note": "Selected TEST_RULE.",
        "ambiguity_detected": False,
        "contradiction_detected": False,
        "gradcam_heatmap_base64": "aGVhdG1hcA==",
        "gradcam_overlay_base64": "b3ZlcmxheQ==",
        "lesion_mask_base64": "bWFzaw==",
    }


def test_predict_response_keeps_legacy_fields_and_adds_reasoning(monkeypatch):
    predictor_stub = ModuleType("predictor")
    predictor_stub.predict_with_gradcam = lambda _: _fake_prediction()
    monkeypatch.setitem(sys.modules, "predictor", predictor_stub)
    sys.modules.pop("main", None)
    main = importlib.import_module("main")

    upload = UploadFile(
        file=BytesIO(b"mock image content"),
        filename="leaf.png",
        headers=Headers({"content-type": "image/png"}),
    )
    response = asyncio.run(main.predict(upload))
    payload = response.model_dump(by_alias=True)

    # Existing response contract.
    assert payload["class"] == "leaf_blast"
    assert payload["confidence"] == 0.91
    assert payload["infected_area_percent"] == 8.5
    assert "gradcam_heatmap_base64" in payload
    assert "gradcam_overlay_base64" in payload
    assert "lesion_mask_base64" in payload

    # New graph, reasoning, and conflict-resolution contract.
    assert payload["final_decision"] == "leaf_blast"
    assert payload["attention_coverage_percent"] == 8.5
    assert payload["matched_rules"][0]["rule_id"] == "TEST_RULE"
    assert payload["ambiguity_detected"] is False
