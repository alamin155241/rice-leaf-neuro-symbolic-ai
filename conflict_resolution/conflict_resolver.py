"""Transparent deterministic scoring for candidate management rules.

Scoring is additive:

* ``safety_priority * 100``
* validation status: system safety 80, expert validated 60,
  pending expert validation 10
* regional applicability: Bangladesh 40, global 10
* exact disease match 30
* exact/small severity set 20, broad severity set 5
* compatible confidence range 15, plus 5 for an explicit upper bound
* the rule's explicit numeric ``priority``

The high safety multiplier enforces the requested precedence. Remaining terms
favour Bangladesh-specific, disease-specific, severity-specific rules over
general management. Ties are resolved lexically by rule ID.
"""

from __future__ import annotations

from typing import Any

from neuro_symbolic.artifact_loader import load_rules
from neuro_symbolic.class_mapping import to_research_label


FALLBACK_RECOMMENDATION = (
    "Retake the image or consult a local agricultural expert."
)


def resolve_management_rules(
    *,
    final_class: str,
    runtime_mode: str,
    safety_safeguards: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Resolve post-diagnostic guidance without affecting the diagnosis.

    Phase 5 management records remain advisory unless their stored runtime and
    validation metadata explicitly make them actionable. System safeguards are
    application policy and may provide conservative retake/consult guidance.
    """
    safeguards = safety_safeguards or []
    if safeguards:
        selected = safeguards[0]
        return {
            "selected_rule": selected,
            "recommendation": selected["recommendation"],
            "warning": selected["warning"],
            "actionable": True,
            "advisory_only": False,
            "validation_status": selected["validation_status"],
            "runtime_state": selected["runtime_state"],
            "sources": [selected["source"]],
            "candidate_rules": safeguards,
            "policy_note": (
                "A deterministic safety safeguard was selected. It is not "
                "scientific phenotype evidence and did not affect fusion scores."
            ),
        }

    research_label = to_research_label(final_class)
    mode_states = {
        "production": {"ACTIVE_CANDIDATE"},
        "staging": {"ACTIVE_CANDIDATE", "STAGING_CANDIDATE"},
        "research": {
            "ACTIVE_CANDIDATE",
            "STAGING_CANDIDATE",
            "EVIDENCE_SUPPORTED_HOLD",
        },
    }[runtime_mode]
    candidates = [
        dict(rule)
        for rule in load_rules()
        if rule.get("rule_type") == "management"
        and rule.get("class_name") == research_label
        and rule.get("runtime_state") in mode_states
    ]
    candidates.sort(
        key=lambda rule: (
            rule.get("runtime_state") != "ACTIVE_CANDIDATE",
            str(rule.get("rule_id", "")),
        )
    )
    # The supplied Phase 5 rules carry NEEDS_* validation categories. Do not
    # reinterpret these as expert validation or validated treatment.
    actionable = [
        rule
        for rule in candidates
        if rule.get("runtime_state") == "ACTIVE_CANDIDATE"
        and rule.get("runtime_enabled") is True
        and rule.get("validation", {}).get("category")
        in {"EXPERT_VALIDATED", "VALIDATED"}
    ]
    selected = actionable[0] if actionable else None
    if selected is None:
        return {
            "selected_rule": None,
            "recommendation": FALLBACK_RECOMMENDATION,
            "warning": (
                "No authoritative, actionable management rule is available. "
                "Research candidates are advisory only."
            ),
            "actionable": False,
            "advisory_only": True,
            "validation_status": (
                candidates[0].get("validation", {}).get("category")
                if candidates
                else "NO_MATCHING_MANAGEMENT_RULE"
            ),
            "runtime_state": (
                candidates[0].get("runtime_state") if candidates else "NO_MATCH"
            ),
            "sources": [
                {
                    "rule_id": rule.get("rule_id"),
                    "source_document_id": rule.get("provenance", {}).get(
                        "source_document_id"
                    ),
                    "citation": rule.get("provenance", {}).get("citation"),
                }
                for rule in candidates
            ],
            "candidate_rules": candidates,
            "policy_note": (
                "Held, staging, incomplete, or unvalidated records were not "
                "presented as actionable treatment instructions."
            ),
        }
    return {
        "selected_rule": selected,
        "recommendation": selected["conclusion"]["raw_text"],
        "warning": "",
        "actionable": True,
        "advisory_only": False,
        "validation_status": selected["validation"]["category"],
        "runtime_state": selected["runtime_state"],
        "sources": [selected["provenance"]],
        "candidate_rules": candidates,
        "policy_note": "Selected from authoritative Phase 5 management records.",
    }


def _confidence_is_compatible(rule: dict[str, Any], confidence: float) -> bool:
    minimum = float(rule.get("minimum_confidence", 0.0))
    maximum_value = rule.get("maximum_confidence")
    maximum = float(maximum_value) if maximum_value is not None else None
    return confidence >= minimum and (maximum is None or confidence <= maximum)


def score_rule(
    rule: dict[str, Any],
    *,
    disease: str,
    severity: str,
    confidence: float,
) -> tuple[float, dict[str, float]]:
    """Return a rule's score and auditable score components."""
    safety_score = float(rule.get("safety_priority", 0)) * 100.0

    validation_status = str(rule.get("validation_status", ""))
    validation_score = {
        "system_safety_rule": 80.0,
        "expert_validated": 60.0,
        "pending_expert_validation": 10.0,
    }.get(validation_status, 0.0)

    regions = [str(item).lower() for item in rule.get("regional_applicability", [])]
    if "bangladesh" in regions:
        regional_score = 40.0
    elif "global" in regions:
        regional_score = 10.0
    else:
        regional_score = 0.0

    rule_disease = str(rule.get("disease", "")).lower()
    disease_score = 30.0 if rule_disease == disease.lower() else 0.0

    severities = [str(item).lower() for item in rule.get("applicable_severities", [])]
    if severity.lower() in severities:
        severity_score = 20.0 if len(severities) <= 2 else 5.0
    elif "*" in severities:
        severity_score = 5.0
    else:
        severity_score = 0.0

    confidence_score = 0.0
    if _confidence_is_compatible(rule, confidence):
        confidence_score = 15.0
        if rule.get("maximum_confidence") is not None:
            confidence_score += 5.0

    explicit_priority = float(rule.get("priority", 0))
    components = {
        "safety": safety_score,
        "validation": validation_score,
        "regional": regional_score,
        "disease_specificity": disease_score,
        "severity_specificity": severity_score,
        "confidence_compatibility": confidence_score,
        "explicit_priority": explicit_priority,
    }
    return sum(components.values()), components


def resolve_rule_conflicts(
    candidate_rules: list[dict[str, Any]],
    *,
    disease: str,
    severity: str,
    confidence: float,
) -> dict[str, Any]:
    """Select one candidate rule using deterministic, auditable precedence."""
    if not candidate_rules:
        return {
            "selected_rule": None,
            "selected_rule_id": None,
            "selected_recommendation": FALLBACK_RECOMMENDATION,
            "selected_warning": (
                "No applicable knowledge rule was found; manual review is required."
            ),
            "conflicts_detected": [],
            "rejected_rule_ids": [],
            "resolution_explanation": (
                "No rule matched. Applied the conservative fallback recommendation."
            ),
            "resolution_score": 0.0,
        }

    scored: list[tuple[float, str, dict[str, Any], dict[str, float]]] = []
    for rule in candidate_rules:
        score, components = score_rule(
            rule,
            disease=disease,
            severity=severity,
            confidence=confidence,
        )
        rule_id = str(rule.get("rule_id", "UNIDENTIFIED_RULE"))
        scored.append((score, rule_id, rule, components))

    scored.sort(key=lambda item: (-item[0], item[1]))
    selected_score, selected_id, selected_rule, components = scored[0]
    rejected_rule_ids = [item[1] for item in scored[1:]]

    conflicts_detected: list[str] = []
    if len(scored) > 1:
        recommendations = {
            str(item[2].get("recommendation", "")).strip() for item in scored
        }
        warnings = {str(item[2].get("warning", "")).strip() for item in scored}
        if len(recommendations) > 1:
            conflicts_detected.append(
                "Candidate rules proposed different recommendations."
            )
        if len(warnings) > 1:
            conflicts_detected.append(
                "Candidate rules proposed different warnings."
            )

    component_text = ", ".join(
        f"{name}={value:.0f}" for name, value in components.items()
    )
    resolution_explanation = (
        f"Selected {selected_id} with score {selected_score:.0f} "
        f"({component_text})."
    )
    if rejected_rule_ids:
        resolution_explanation += (
            " Rejected lower-scoring rules: " + ", ".join(rejected_rule_ids) + "."
        )

    return {
        "selected_rule": dict(selected_rule),
        "selected_rule_id": selected_id,
        "selected_recommendation": str(
            selected_rule.get("recommendation", FALLBACK_RECOMMENDATION)
        ),
        "selected_warning": str(selected_rule.get("warning", "")),
        "conflicts_detected": conflicts_detected,
        "rejected_rule_ids": rejected_rule_ids,
        "resolution_explanation": resolution_explanation,
        "resolution_score": selected_score,
    }
