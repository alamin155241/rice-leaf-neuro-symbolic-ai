"""Observation preparation that never fabricates image phenotype features."""

from __future__ import annotations

from typing import Any

from .artifact_loader import load_json_artifact
from .class_mapping import to_research_label
from .observation_vocabulary import observation_schema_response
from .observation_vocabulary import validate_observations
from .schemas import CNNOutput, GuidedObservations


class GuidedObservationPolicyError(ValueError):
    """Raised when unvalidated guided text is disabled by server policy."""


def _is_supplied(value: Any) -> bool:
    return value not in (None, "", [], {})


def prepare_observations(
    cnn_output: CNNOutput,
    guided: GuidedObservations | None,
    attention_coverage_percent: float,
    severity_heuristic: str,
    *,
    runtime_mode: str,
    allow_unvalidated_guided: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    template = load_json_artifact("phase6_observation_schema")
    visual = dict(template["visual_features"])
    provided: dict[str, Any] = {}
    sources: dict[str, str] = {}
    validation_records: list[dict[str, Any]] = []
    unvalidated_fields: list[str] = []
    if guided is not None:
        provided = {
            key: value
            for key, value in guided.model_dump(exclude_none=True).items()
            if _is_supplied(value)
        }
        normalized, validation_records, unvalidated_fields = (
            validate_observations(provided)
        )
        if (
            unvalidated_fields
            and runtime_mode in {"staging", "production"}
            and not allow_unvalidated_guided
        ):
            fields = ", ".join(sorted(unvalidated_fields))
            raise GuidedObservationPolicyError(
                "Unvalidated guided observations are disabled by server policy. "
                f"Fields: {fields}."
            )
        visual.update(normalized)
        sources.update({key: "user_confirmed" for key in provided})

    sample = {
        "sample_id": cnn_output.sample_id,
        "cnn_prediction": {
            "predicted_class": to_research_label(cnn_output.predicted_class),
            "confidence": cnn_output.confidence,
            "class_probabilities": {
                to_research_label(key): value
                for key, value in cnn_output.class_probabilities.items()
            },
        },
        "visual_features": visual,
        "environment_context": dict(template["environment_context"]),
    }

    observation_result = {
        "input_mode": "guided_phenotype" if provided else "image_only",
        "provided_observations": provided,
        "provided_observed_features": validation_records,
        "normalized_observations": {
            key: value
            for key, value in visual.items()
            if _is_supplied(value)
        },
        "observation_sources": sources,
        "missing_required_or_relevant_features": [
            key for key, value in visual.items() if not _is_supplied(value)
        ],
        "categorical_vocabulary_status": "provenance_backed_v1",
        "categorical_values_enum_validated": (
            not unvalidated_fields
            and any(record["enum_validated"] for record in validation_records)
        ),
        "observation_validation": validation_records,
        "unvalidated_fields": sorted(unvalidated_fields),
        "warnings": (
            [
                "Unvalidated guided free text was accepted in research mode; "
                "it is not categorical-enum evidence."
            ]
            if unvalidated_fields and runtime_mode == "research"
            else [
                "Unvalidated guided free text was accepted by explicit server "
                "policy."
            ]
            if unvalidated_fields
            else []
        ),
        "attention_context": {
            "attention_coverage_percent": attention_coverage_percent,
            "severity_heuristic": severity_heuristic,
            "source": "gradcam_attention_heuristic",
            "used_as_phenotype_observation": False,
        },
    }
    return sample, observation_result
