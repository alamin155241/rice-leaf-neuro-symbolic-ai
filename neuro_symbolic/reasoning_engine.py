"""Phase 6 notebook reasoning algorithm, refactored for cached runtime use."""

from __future__ import annotations

import re
from typing import Any

import numpy as np

from .artifact_loader import load_json_artifact, load_rules


SYNONYM_MAP = {
    "spindle shaped": "spindle",
    "spindle-shaped": "spindle",
    "elliptical": "elliptical",
    "oval": "oval",
    "oblong": "oblong",
    "narrow": "narrow",
    "grayish": "gray",
    "greyish": "gray",
    "grey": "gray",
    "whitish": "white",
    "reddish brown": "reddish brown",
    "reddish-brown": "reddish brown",
    "chlorotic": "yellow",
    "yellow halo": "yellow halo",
    "light brown": "light brown",
    "dark brown": "dark brown",
    "leaf blade": "leaf blade",
    "leaf tip": "leaf tip",
    "leaf edges": "leaf edge",
    "leaf edge": "leaf edge",
    "mature leaves": "mature leaf",
    "visibly healthy": "visibly healthy",
    "high vigor": "high vigor",
}

CONDITION_MATCH = "MATCH"
CONDITION_NO_MATCH = "NO_MATCH"
CONDITION_CONTRADICTION = "CONTRADICTION"
CONDITION_NOT_PROVIDED = "NOT_PROVIDED"

OUTCOME_DIAGNOSTIC_SUPPORT = "DIAGNOSTIC_SUPPORT"
OUTCOME_DIAGNOSTIC_CONTRADICTION = "DIAGNOSTIC_CONTRADICTION"
OUTCOME_PHENOTYPE_INFERENCE = "PHENOTYPE_INFERENCE"
OUTCOME_ENVIRONMENTAL_SUPPORT = "ENVIRONMENTAL_SUPPORT"
OUTCOME_DIFFERENTIAL = "DIFFERENTIAL"
OUTCOME_SEVERITY = "SEVERITY"
OUTCOME_MANAGEMENT = "MANAGEMENT"
OUTCOME_REVIEW_REQUIRED = "REVIEW_REQUIRED"
OUTCOME_SENESCENCE = "SENESCENCE"
OUTCOME_UNCERTAINTY = "UNCERTAINTY"
OUTCOME_OTHER = "OTHER"

NEGATION_TOKENS = {
    "absent",
    "lack",
    "lacks",
    "lacking",
    "no",
    "not",
    "without",
}
SEMANTIC_NOISE_TOKENS = {
    "a",
    "an",
    "and",
    "approximately",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "by",
    "characterized",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "lesion",
    "more",
    "observed",
    "occurs",
    "of",
    "on",
    "or",
    "present",
    "starts",
    "symptom",
    "the",
    "to",
    "with",
}
TOKEN_CANONICALIZATION = {
    "centers": "center",
    "dots": "dot",
    "edges": "edge",
    "halos": "halo",
    "leaves": "leaf",
    "lesions": "lesion",
    "specks": "speck",
    "spots": "spot",
    "stages": "stage",
    "tissues": "tissue",
}

DIAGNOSTIC_TYPES = {
    "diagnostic",
    "healthy_baseline",
    "severity",
    "supporting_knowledge",
}
NON_DIAGNOSTIC_TYPES = {"management"}


def _config() -> dict[str, Any]:
    return load_json_artifact("phase6_reasoning_config")


def norm_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).lower().strip().replace("_", " ").replace("°c", " c")
    text = re.sub(r'[^a-z0-9.%<>=\-\s"]+', " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\b(\d+)\.0\b", r"\1", text)
    for source, target in sorted(SYNONYM_MAP.items(), key=lambda item: -len(item[0])):
        text = text.replace(source, target)
    return text


def flatten_observations(
    sample: dict[str, Any], *, include_cnn_label_for_parity: bool = False
) -> list[str]:
    """Flatten supplied observations.

    ``include_cnn_label_for_parity`` remains in the signature for callers that
    used the Phase 6 API, but it is intentionally ignored. A CNN output is a
    prediction, never an independently observed phenotype.
    """
    _ = include_cnn_label_for_parity
    visual = sample.get("visual_features", {})
    environment = sample.get("environment_context", {})
    observations: list[str] = []
    for key, value in visual.items():
        if value is None or value == "" or value == []:
            continue
        if isinstance(value, list):
            observations.extend(norm_text(item) for item in value)
        elif isinstance(value, bool):
            observations.append(norm_text(key if value else f"{key} absent"))
            if value:
                observations.append(norm_text(f"{key} present"))
        else:
            observations.extend((norm_text(value), norm_text(f"{key} {value}")))
    if environment.get("enabled"):
        for key, value in environment.items():
            if key != "enabled" and value not in (None, ""):
                observations.extend((norm_text(value), norm_text(f"{key} {value}")))
    return sorted({value for value in observations if value})


def token_set(text: str) -> set[str]:
    stop = {
        "is", "are", "the", "a", "an", "of", "on", "in", "and", "or",
        "with", "has", "have", "be", "to", "for", "by", "as", "at", "it",
        "this", "that", "may", "can", "will", "approximately",
    }
    return {
        TOKEN_CANONICALIZATION.get(token, token)
        for token in norm_text(text).split()
        if len(token) > 1 and token not in stop
    }


def _has_negation(text: str) -> bool:
    normalized = norm_text(text)
    return any(
        re.search(rf"\b{re.escape(token)}\b", normalized)
        for token in NEGATION_TOKENS
    )


def _semantic_tokens(text: str) -> set[str]:
    tokens = {
        TOKEN_CANONICALIZATION.get(token, token)
        for token in re.findall(r"[a-z0-9.%\-]+", norm_text(text))
        if len(token) > 1
    }
    return tokens - SEMANTIC_NOISE_TOKENS - NEGATION_TOKENS - {
        "identified",
        "less",
    }


def _condition_alternatives(text: str) -> list[set[str]]:
    """Return only alternatives explicitly separated by the source word OR."""
    normalized = norm_text(text)
    parts = re.split(r"\s+or\s+", normalized)
    return [tokens for part in parts if (tokens := _semantic_tokens(part))]


def _observation_evidence(
    observations: list[str],
) -> tuple[list[dict[str, Any]], set[str], set[str]]:
    evidence: list[dict[str, Any]] = []
    positive_tokens: set[str] = set()
    negative_tokens: set[str] = set()
    for observation in observations:
        normalized = norm_text(observation)
        tokens = _semantic_tokens(normalized)
        if not tokens:
            continue
        negative = _has_negation(normalized)
        evidence.append(
            {
                "text": normalized,
                "tokens": tokens,
                "polarity": "ABSENT" if negative else "PRESENT",
            }
        )
        if negative:
            negative_tokens.update(tokens)
        else:
            positive_tokens.update(tokens)
    return evidence, positive_tokens, negative_tokens


def _condition_is_circular_or_etiological(
    rule: dict[str, Any], condition_text: str
) -> bool:
    """Reject prior diagnoses and pathogen identity as phenotype evidence."""
    condition = norm_text(condition_text)
    target = norm_text(rule.get("class_name", ""))
    if target and target in condition:
        return True

    target_markers = {
        "Leaf Blast": {"blast fungus", "blast spot", "blast lesion"},
        "Narrow Brown Leaf Spot": {"nbls"},
    }.get(str(rule.get("class_name", "")), set())
    if any(marker in condition for marker in target_markers):
        return True

    return bool(
        re.search(
            r"\b(causal fungus|causal organism|causal agent|organism is)\b",
            condition,
        )
    )


def evaluate_condition(
    rule: dict[str, Any], condition_text: str, observations: list[str]
) -> dict[str, Any]:
    """Evaluate one mandatory condition without fuzzy compensation."""
    normalized = norm_text(condition_text)
    required_polarity = "ABSENT" if _has_negation(normalized) else "PRESENT"
    alternatives = _condition_alternatives(normalized)
    evidence, positive_tokens, negative_tokens = _observation_evidence(observations)

    if _condition_is_circular_or_etiological(rule, normalized):
        return {
            "condition_text": condition_text,
            "normalized_condition": normalized,
            "state": CONDITION_NOT_PROVIDED,
            "required_polarity": required_polarity,
            "alternatives": [sorted(item) for item in alternatives],
            "matched_observations": [],
            "reason": "CIRCULAR_OR_ETIOLOGICAL_PREREQUISITE",
        }
    if not alternatives:
        return {
            "condition_text": condition_text,
            "normalized_condition": normalized,
            "state": CONDITION_NOT_PROVIDED,
            "required_polarity": required_polarity,
            "alternatives": [],
            "matched_observations": [],
            "reason": "NO_SEMANTIC_CONCEPTS",
        }

    matching_tokens = negative_tokens if required_polarity == "ABSENT" else positive_tokens
    opposing_tokens = positive_tokens if required_polarity == "ABSENT" else negative_tokens
    matched_alternative = next(
        (alternative for alternative in alternatives if alternative <= matching_tokens),
        None,
    )
    opposing_alternative = next(
        (alternative for alternative in alternatives if alternative <= opposing_tokens),
        None,
    )
    # An explicit absence of the entity (for example "no halo") contradicts
    # a more specific positive requirement such as "light brown halo".
    partial_opposition = any(
        opposing_tokens
        and opposing_tokens <= alternative
        and bool(opposing_tokens & {"halo", "lesion", "spot", "spindle"})
        for alternative in alternatives
    )

    if opposing_alternative is not None or partial_opposition:
        state = CONDITION_CONTRADICTION
        selected = opposing_alternative or set()
        reason = "OPPOSITE_POLARITY_OBSERVED"
    elif matched_alternative is not None:
        state = CONDITION_MATCH
        selected = matched_alternative
        reason = "ALL_REQUIRED_CONCEPTS_OBSERVED"
    else:
        required_tokens = set().union(*alternatives)
        if required_tokens & (positive_tokens | negative_tokens):
            state = CONDITION_NO_MATCH
            reason = "PARTIAL_OR_INCOMPATIBLE_EVIDENCE"
        else:
            state = CONDITION_NOT_PROVIDED
            reason = "REQUIRED_CONCEPT_NOT_PROVIDED"
        selected = set()

    matched_observations = sorted(
        {
            item["text"]
            for item in evidence
            if selected and item["tokens"] & selected
        }
    )
    return {
        "condition_text": condition_text,
        "normalized_condition": normalized,
        "state": state,
        "required_polarity": required_polarity,
        "alternatives": [sorted(item) for item in alternatives],
        "matched_observations": matched_observations,
        "reason": reason,
    }


def rule_is_complete(rule: dict[str, Any]) -> bool:
    return bool(
        norm_text(rule.get("condition_text"))
        and norm_text(rule.get("conclusion", {}).get("raw_text"))
        and rule.get("runtime_state") != "HOLD_PARSE_INCOMPLETE"
    )


def rule_is_image_relevant(rule: dict[str, Any], sample: dict[str, Any]) -> bool:
    rule_type = rule.get("rule_type", "")
    if rule_type in NON_DIAGNOSTIC_TYPES:
        return False
    if rule_type == "environmental_support":
        return bool(sample.get("environment_context", {}).get("enabled"))
    return rule_type in DIAGNOSTIC_TYPES


def rule_allowed_in_mode(rule: dict[str, Any], mode: str) -> bool:
    state = rule.get("runtime_state", "")
    if mode == "production":
        return state == "ACTIVE_CANDIDATE"
    if mode == "staging":
        return state in {"ACTIVE_CANDIDATE", "STAGING_CANDIDATE"}
    return state in {
        "ACTIVE_CANDIDATE",
        "STAGING_CANDIDATE",
        "EVIDENCE_SUPPORTED_HOLD",
    }


def phrase_match_score(
    phrase: str, observations: list[str]
) -> tuple[float, list[str]]:
    """Backward-compatible strict phrase matcher.

    It no longer returns fractional token overlap. A phrase matches only when
    one explicitly declared alternative is completely present with the same
    polarity.
    """
    synthetic_rule = {"class_name": "", "rule_type": "diagnostic"}
    result = evaluate_condition(synthetic_rule, phrase, observations)
    return (
        (1.0, result["matched_observations"])
        if result["state"] == CONDITION_MATCH
        else (0.0, [])
    )


def _conclusion_supports_target(rule: dict[str, Any]) -> bool:
    conclusion = norm_text(rule.get("conclusion", {}).get("raw_text", ""))
    target = norm_text(rule.get("class_name", ""))
    if target and conclusion == target:
        return True
    if "healthy rice leaf candidate" in conclusion:
        return True
    if re.search(r"\b(support|supports)\b.*\bdiagnosis\b", conclusion):
        return True
    if "evidence supports diagnosis" in conclusion:
        return True
    if target and target in conclusion and any(
        cue in conclusion
        for cue in {"characteristic", "identified as", "supports diagnosis"}
    ):
        return True
    return False


def conclusion_is_diagnostic(rule: dict[str, Any]) -> bool:
    """Compatibility wrapper for explicit positive diagnostic conclusions."""
    return _conclusion_supports_target(rule)


def classify_rule_outcome(rule: dict[str, Any]) -> str:
    """Classify what the rule concludes before allowing diagnostic scoring."""
    rule_type = str(rule.get("rule_type", ""))
    conclusion = norm_text(rule.get("conclusion", {}).get("raw_text", ""))

    if rule_type == "management":
        return OUTCOME_MANAGEMENT
    if "expert review" in conclusion:
        return OUTCOME_REVIEW_REQUIRED
    if "uncertain diagnosis" in conclusion:
        return OUTCOME_UNCERTAINTY
    if "natural senescence" in conclusion or "lag phase yellowing" in conclusion:
        return OUTCOME_SENESCENCE
    if "disease affected rice leaf" in conclusion:
        return OUTCOME_DIAGNOSTIC_CONTRADICTION
    if any(cue in conclusion for cue in {"confused with", "mistakable for"}):
        return OUTCOME_DIFFERENTIAL
    if rule_type == "environmental_support":
        return OUTCOME_ENVIRONMENTAL_SUPPORT
    if rule_type == "severity":
        return OUTCOME_SEVERITY
    if _conclusion_supports_target(rule):
        return OUTCOME_DIAGNOSTIC_SUPPORT
    if rule_type in {"diagnostic", "healthy_baseline", "supporting_knowledge"}:
        return OUTCOME_PHENOTYPE_INFERENCE
    return OUTCOME_OTHER


def evaluate_rule(
    rule: dict[str, Any],
    observations: list[str],
    min_condition_score: float = 0.50,
    min_pattern_score: float = 0.42,
) -> dict[str, Any]:
    # Retained in the signature for callers written against Phase 6. Semantic
    # firing no longer uses permissive numeric thresholds.
    _ = (min_condition_score, min_pattern_score)
    condition_parts = rule.get("conditions", []) or [
        {"raw_text": rule.get("condition_text", "")}
    ]
    condition_states: list[dict[str, Any]] = []
    matched_observations: list[str] = []
    for condition in condition_parts:
        result = evaluate_condition(
            rule, condition.get("raw_text", ""), observations
        )
        condition_states.append(result)
        matched_observations.extend(result["matched_observations"])
    matched_condition_count = sum(
        item["state"] == CONDITION_MATCH for item in condition_states
    )
    condition_score = (
        matched_condition_count / len(condition_states) if condition_states else 0.0
    )
    fired = bool(condition_states) and all(
        item["state"] == CONDITION_MATCH for item in condition_states
    )
    outcome_type = classify_rule_outcome(rule)
    score_eligible = fired and outcome_type == OUTCOME_DIAGNOSTIC_SUPPORT
    return {
        "fired": bool(fired),
        "condition_score": round(condition_score, 4),
        # Preserved for API compatibility. Conclusions are outputs and are not
        # searched in observations or used for firing.
        "conclusion_score": 0.0,
        "combined_match": round(condition_score, 4),
        "evidence_mode": outcome_type,
        "outcome_type": outcome_type,
        "score_eligible": score_eligible,
        "condition_logic": "ALL_MANDATORY",
        "condition_states": condition_states,
        "conclusion_used_for_firing": False,
        "matched_observations": sorted(set(matched_observations)),
    }


def _normalized_soft_scores(raw_scores: dict[str, float]) -> dict[str, float]:
    classes = _config()["supported_classes"]
    values = np.array(
        [max(0.0, raw_scores.get(class_name, 0.0)) for class_name in classes],
        dtype=float,
    )
    if values.sum() == 0:
        return {class_name: 0.0 for class_name in classes}
    probabilities = values / values.sum()
    return {
        class_name: round(float(value), 4)
        for class_name, value in zip(classes, probabilities)
    }


def reasoning_engine(
    sample: dict[str, Any],
    mode: str = "research",
    *,
    include_cnn_label_for_parity: bool = False,
) -> dict[str, Any]:
    config = _config()
    classes = config["supported_classes"]
    observations = flatten_observations(
        sample, include_cnn_label_for_parity=include_cnn_label_for_parity
    )
    raw_scores = {class_name: 0.0 for class_name in classes}
    fired_rules: list[dict[str, Any]] = []
    non_scoring_rule_ids: list[str] = []
    trace: list[dict[str, Any]] = []

    for rule in load_rules():
        if not rule_is_complete(rule):
            continue
        if not rule_allowed_in_mode(rule, mode):
            continue
        if not rule_is_image_relevant(rule, sample):
            continue
        match = evaluate_rule(rule, observations)
        trace.append(
            {
                "rule_id": rule.get("rule_id"),
                "condition_text": rule.get("condition_text"),
                "runtime_state": rule.get("runtime_state"),
                "fired": match["fired"],
                "outcome_type": match["outcome_type"],
                "score_eligible": match["score_eligible"],
                "match": match,
            }
        )
        if not match["fired"]:
            continue
        if not match["score_eligible"]:
            non_scoring_rule_ids.append(str(rule.get("rule_id", "")))
            continue
        class_name = rule.get("class_name")
        if class_name not in raw_scores:
            continue
        contribution = (
            float(rule.get("provisional_weight", 0.5))
            * float(config["state_factors"].get(rule.get("runtime_state"), 0.5))
            * float(config["type_factors"].get(rule.get("rule_type"), 0.5))
            * match["combined_match"]
        )
        raw_scores[class_name] += contribution
        provenance = rule.get("provenance", {})
        fired_rules.append(
            {
                "rule_id": rule.get("rule_id"),
                "class_name": class_name,
                "rule_type": rule.get("rule_type"),
                "runtime_state": rule.get("runtime_state"),
                "runtime_enabled": rule.get("runtime_enabled"),
                "validation": rule.get("validation"),
                "condition_text": rule.get("condition_text"),
                "conclusion_text": rule.get("conclusion", {}).get("raw_text"),
                "rule_weight": float(rule.get("provisional_weight", 0.5)),
                "score_contribution": round(contribution, 4),
                "match": match,
                "source_document_id": provenance.get("source_document_id"),
                "citation": provenance.get("citation"),
                "evidence_ids": provenance.get("evidence_ids", []),
                "master_record_id": provenance.get("master_record_id"),
                "source_record_id": provenance.get("source_record_id"),
                "source_rule_record": rule,
            }
        )

    scores = _normalized_soft_scores(raw_scores)
    ranking = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    prediction = ranking[0][0] if ranking and ranking[0][1] > 0 else "Uncertain"
    top_score = ranking[0][1] if ranking else 0.0
    second_score = ranking[1][1] if len(ranking) > 1 else 0.0
    margin = round(top_score - second_score, 4)
    if not fired_rules:
        confidence_label = "INSUFFICIENT_SYMBOLIC_EVIDENCE"
        status = "insufficient_observation_evidence"
    elif top_score >= 0.65 and margin >= 0.25:
        confidence_label, status = "HIGH", "completed"
    elif top_score >= 0.45 and margin >= 0.10:
        confidence_label, status = "MODERATE", "completed"
    else:
        confidence_label, status = "LOW_OR_CONFLICTED", "completed"
    fired_rules.sort(key=lambda item: item["score_contribution"], reverse=True)
    evidence_ids = sorted(
        {
            evidence_id
            for rule in fired_rules
            for evidence_id in rule.get("evidence_ids", [])
        }
    )
    return {
        "sample_id": sample.get("sample_id", ""),
        "reasoning_mode": mode,
        "status": status,
        "symbolic_prediction": prediction,
        "symbolic_score": round(top_score, 4),
        "confidence_label": confidence_label,
        "score_margin": margin,
        "disease_scores": scores,
        "raw_evidence_scores": {
            key: round(value, 4) for key, value in raw_scores.items()
        },
        "matched_rule_count": len(fired_rules),
        "matched_rules": fired_rules,
        "matched_rule_ids": [rule["rule_id"] for rule in fired_rules],
        "non_scoring_fired_rule_ids": non_scoring_rule_ids,
        "matched_evidence_ids": evidence_ids,
        "observations_used": observations,
        "reasoning_trace": trace,
        "limitations": [
            "Only user-confirmed structured observations are treated as phenotype evidence.",
            "The CNN predicted class is excluded from runtime symbolic observations.",
            "All mandatory rule conditions must match with compatible semantic polarity.",
            "Rule conclusions are outputs and are not required as observations.",
            "Only explicit diagnostic-support outcomes contribute disease-class scores.",
        ],
        "warnings": [
            "Research mode may use rules that are not runtime-active."
            if mode == "research"
            else "",
            "This engine does not replace agronomist or plant-pathologist assessment.",
        ],
    }
