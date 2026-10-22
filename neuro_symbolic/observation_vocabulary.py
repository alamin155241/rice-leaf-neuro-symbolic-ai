"""Provenance-backed validation for Phase 6 guided observations."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator

from .artifact_loader import load_json_artifact


class ObservationVocabularyValidationError(ValueError):
    """Raised when a categorical value is outside its closed vocabulary."""

    def __init__(self, field: str, allowed_values: list[str]) -> None:
        self.field = field
        self.allowed_values = allowed_values
        super().__init__(f"Unsupported categorical value for '{field}'.")

    def api_detail(self) -> dict[str, Any]:
        return {
            "error": "unsupported_observation_value",
            "field": self.field,
            "message": str(self),
            "allowed_values": self.allowed_values,
        }


def _comparison_key(value: str) -> str:
    """Apply only the non-semantic comparison rules declared by the artifact."""
    return value.strip().casefold()


@lru_cache(maxsize=1)
def load_observation_vocabulary() -> dict[str, Any]:
    vocabulary = load_json_artifact("observation_vocabulary")
    schema = load_json_artifact("observation_vocabulary_schema")
    errors = sorted(
        Draft202012Validator(schema).iter_errors(vocabulary),
        key=lambda error: list(error.absolute_path),
    )
    if errors:
        raise RuntimeError(
            "Observation vocabulary does not match its schema: "
            f"{errors[0].message}"
        )

    phase6_fields = set(
        load_json_artifact("phase6_observation_schema")["visual_features"]
    )
    vocabulary_fields = set(vocabulary["fields"])
    if vocabulary_fields != phase6_fields:
        missing = sorted(phase6_fields - vocabulary_fields)
        extra = sorted(vocabulary_fields - phase6_fields)
        raise RuntimeError(
            "Observation vocabulary fields do not exactly match Phase 6: "
            f"missing={missing}, extra={extra}"
        )

    for field_name, field in vocabulary["fields"].items():
        values = field.get("allowed_values") or []
        lookup: dict[str, str] = {}
        for value in values:
            canonical = value["canonical_value"]
            candidates = [
                canonical,
                *value.get("original_values", []),
                *[item["value"] for item in value.get("aliases", [])],
            ]
            for candidate in candidates:
                key = _comparison_key(candidate)
                previous = lookup.get(key)
                if previous is not None and previous != canonical:
                    raise RuntimeError(
                        "Observation vocabulary alias collision for "
                        f"{field_name}: {candidate}"
                    )
                lookup[key] = canonical
    return vocabulary


def _categorical_lookup(field: dict[str, Any]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for value in field.get("allowed_values") or []:
        candidates = [
            value["canonical_value"],
            *value.get("original_values", []),
            *[item["value"] for item in value.get("aliases", [])],
        ]
        for candidate in candidates:
            lookup[_comparison_key(candidate)] = value
    return lookup


def _validation_record(
    *,
    field_name: str,
    submitted_value: Any,
    normalized_value: Any,
    enum_validated: bool,
    validation_type: str,
    provenance: dict[str, Any] | None = None,
    normalization: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "field": field_name,
        "submitted_value": submitted_value,
        "normalized_value": normalized_value,
        "value": normalized_value,
        "source": "user_confirmed",
        "enum_validated": enum_validated,
        "validation_type": validation_type,
        "vocabulary_provenance": provenance,
        "normalization": normalization,
    }


def validate_observations(
    provided: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    """Normalize closed categorical values and identify unvalidated free text."""
    vocabulary = load_observation_vocabulary()
    normalized: dict[str, Any] = {}
    records: list[dict[str, Any]] = []
    unvalidated_fields: list[str] = []

    for field_name, submitted in provided.items():
        field = vocabulary["fields"][field_name]
        if isinstance(submitted, bool):
            normalized[field_name] = submitted
            records.append(
                _validation_record(
                    field_name=field_name,
                    submitted_value=submitted,
                    normalized_value=submitted,
                    enum_validated=False,
                    validation_type="schema_defined_boolean",
                )
            )
            continue

        if isinstance(submitted, (int, float)):
            normalized[field_name] = submitted
            records.append(
                _validation_record(
                    field_name=field_name,
                    submitted_value=submitted,
                    normalized_value=submitted,
                    enum_validated=False,
                    validation_type="schema_defined_number",
                )
            )
            continue

        if field["categorical_values_available"]:
            lookup = _categorical_lookup(field)
            matched = lookup.get(_comparison_key(submitted))
            if matched is None:
                raise ObservationVocabularyValidationError(
                    field_name,
                    [
                        item["canonical_value"]
                        for item in field["allowed_values"]
                    ],
                )
            canonical = matched["canonical_value"]
            submitted_key = _comparison_key(submitted)
            canonical_key = _comparison_key(canonical)
            matched_alias = next(
                (
                    alias
                    for alias in matched.get("aliases", [])
                    if _comparison_key(alias["value"]) == submitted_key
                ),
                None,
            )
            if submitted_key == canonical_key:
                input_kind = "canonical"
                matched_alias = None
            elif matched_alias is not None:
                input_kind = "explicit_alias"
            else:
                input_kind = "source_surface_form"
            normalized[field_name] = canonical
            records.append(
                _validation_record(
                    field_name=field_name,
                    submitted_value=submitted,
                    normalized_value=canonical,
                    enum_validated=True,
                    validation_type="provenance_backed_categorical_enum",
                    provenance=matched["provenance"],
                    normalization={
                        "input_kind": input_kind,
                        "matched_alias": matched_alias,
                    },
                )
            )
            continue

        normalized[field_name] = submitted
        unvalidated_fields.append(field_name)
        records.append(
            _validation_record(
                field_name=field_name,
                submitted_value=submitted,
                normalized_value=submitted,
                enum_validated=False,
                validation_type="unvalidated_guided_free_text",
            )
        )

    return normalized, records, unvalidated_fields


def observation_schema_response() -> dict[str, Any]:
    """Return the complete client-safe vocabulary and field limitations."""
    vocabulary = load_observation_vocabulary()
    fields: dict[str, Any] = {}
    for field_name, field in vocabulary["fields"].items():
        fields[field_name] = {
            "input_types": field["input_types"],
            "categorical_values_available": field[
                "categorical_values_available"
            ],
            "allowed_values": field["allowed_values"],
            "boolean_allowed_values": field["boolean_allowed_values"],
            "enum_validated": field["enum_validated"],
            "numeric_constraints": field["numeric_constraints"],
            "source": field["field_source"],
            "limitations": field["limitations"],
        }
    return {
        "version": vocabulary["version"],
        "generation_policy": vocabulary["generation_policy"],
        "fields": fields,
        "limitations": vocabulary["limitations"],
    }
