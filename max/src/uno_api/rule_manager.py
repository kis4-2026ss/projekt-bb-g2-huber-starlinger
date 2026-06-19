from __future__ import annotations

import uuid
from copy import deepcopy
from typing import Any

from .engine import default_rules, utc_now

ALLOWED_MUTABLE_RULE_TYPES = {
    "turn_modifier",
    "draw_modifier",
    "custom",
}

SUPPORTED_EFFECT_KEYS = {
    "max_plays_per_turn",
    "draw_count",
    "draw_two_penalty",
    "wild_draw_four_penalty",
    "skip_penalty_cards",
    "reverse_penalty_cards",
    "allow_same_type_match",
    "allow_number_on_number",
    "allow_action_on_action",
    "win_hand_count",
}

EFFECT_ALIASES = {
    "max_cards_per_turn": "max_plays_per_turn",
    "cards_per_turn": "max_plays_per_turn",
    "play_limit": "max_plays_per_turn",
    "draw_cards": "draw_count",
    "draw_two_amount": "draw_two_penalty",
    "wild_draw_four_amount": "wild_draw_four_penalty",
    "skip_draw_penalty": "skip_penalty_cards",
    "reverse_draw_penalty": "reverse_penalty_cards",
    "same_type_match": "allow_same_type_match",
    "number_on_number": "allow_number_on_number",
    "action_on_action": "allow_action_on_action",
    "win_threshold": "win_hand_count",
}

INT_EFFECT_KEYS = {
    "max_plays_per_turn",
    "draw_count",
    "draw_two_penalty",
    "wild_draw_four_penalty",
    "skip_penalty_cards",
    "reverse_penalty_cards",
    "win_hand_count",
}

BOOL_EFFECT_KEYS = {
    "allow_same_type_match",
    "allow_number_on_number",
    "allow_action_on_action",
}

ALLOWED_CONDITION_KEYS = {
    "scope",
    "player_id",
    "player_name",
    "top_color",
    "top_value",
    "top_type",
    "top_card",
    "current_player",
    "opponent",
}

ALLOWED_CARD_CONDITION_KEYS = {"color", "value", "type"}
ALLOWED_PLAYER_CONDITION_KEYS = {"id", "name", "hand_count"}


class RuleChangeError(ValueError):
    """Raised when a mutable rule change request is invalid."""


def default_mutable_rules() -> dict[str, Any]:
    return {
        "version": 1,
        "description": "Agent-created rules. These may be changed during a game.",
        "rules": [],
    }


def combined_rules(mutable_rules: dict[str, Any]) -> dict[str, Any]:
    return {
        "base_rules": default_rules(),
        "mutable_rules": mutable_rules,
        "note": "Only mutable_rules may be changed by agents. base_rules are immutable.",
    }


def rule_mechanics(mutable_rules: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    mechanics = {
        "max_plays_per_turn": 1,
        "draw_count": 1,
        "draw_two_penalty": 2,
        "wild_draw_four_penalty": 4,
        "skip_penalty_cards": 0,
        "reverse_penalty_cards": 0,
        "allow_same_type_match": False,
        "allow_number_on_number": False,
        "allow_action_on_action": False,
        "win_hand_count": 0,
        "active_rule_ids": [],
    }
    context = context or {}
    for rule in mutable_rules.get("rules", []):
        if rule.get("status") != "active" or not _condition_applies(rule.get("condition", {}), context):
            continue
        mechanics["active_rule_ids"].append(rule["id"])
        effect = normalize_effect(rule.get("effect", {}))
        for key in INT_EFFECT_KEYS:
            if key in effect:
                mechanics[key] = max(mechanics[key], _positive_int(effect[key], key))
        for key in BOOL_EFFECT_KEYS:
            if key in effect:
                mechanics[key] = mechanics[key] or _bool_value(effect[key], key)
    return mechanics


def add_mutable_rule(
    mutable_rules: dict[str, Any],
    player_id: str,
    rule: dict[str, Any],
) -> dict[str, Any]:
    next_rules = deepcopy(mutable_rules)
    rules = next_rules.setdefault("rules", [])
    normalized = _normalize_rule(rule, player_id)
    if _find_rule(rules, normalized["id"]):
        raise RuleChangeError("A mutable rule with this id already exists.")
    rules.append(normalized)
    next_rules["version"] = int(next_rules.get("version", 1)) + 1
    return next_rules


def modify_mutable_rule(
    mutable_rules: dict[str, Any],
    player_id: str,
    rule_id: str,
    updates: dict[str, Any],
) -> dict[str, Any]:
    next_rules = deepcopy(mutable_rules)
    existing = _find_rule(next_rules.setdefault("rules", []), rule_id)
    if not existing:
        raise RuleChangeError("Mutable rule not found.")
    protected = {"id", "created_by", "created_at"}
    for key, value in updates.items():
        if key in protected:
            continue
        existing[key] = value
    normalized = _normalize_rule(existing, existing["created_by"])
    normalized["modified_by"] = player_id
    normalized["modified_at"] = utc_now()
    existing.clear()
    existing.update(normalized)
    next_rules["version"] = int(next_rules.get("version", 1)) + 1
    return next_rules


def remove_mutable_rule(mutable_rules: dict[str, Any], player_id: str, rule_id: str) -> dict[str, Any]:
    next_rules = deepcopy(mutable_rules)
    rules = next_rules.setdefault("rules", [])
    existing = _find_rule(rules, rule_id)
    if not existing:
        raise RuleChangeError("Mutable rule not found.")
    rules.remove(existing)
    next_rules["version"] = int(next_rules.get("version", 1)) + 1
    next_rules["last_removed_rule"] = {
        "id": rule_id,
        "removed_by": player_id,
        "removed_at": utc_now(),
    }
    return next_rules


def _normalize_rule(rule: dict[str, Any], player_id: str) -> dict[str, Any]:
    if not isinstance(rule, dict):
        raise RuleChangeError("Rule must be a JSON object.")

    title = str(rule.get("title", "")).strip()
    description = str(rule.get("description", "")).strip()
    rule_type = str(rule.get("type", "custom")).strip()

    if not title:
        raise RuleChangeError("Rule title is required.")
    if not description:
        raise RuleChangeError("Rule description is required.")
    if rule_type not in ALLOWED_MUTABLE_RULE_TYPES:
        raise RuleChangeError(f"Rule type must be one of: {', '.join(sorted(ALLOWED_MUTABLE_RULE_TYPES))}.")
    condition = rule.get("condition", {})
    _validate_condition(condition)
    effect = normalize_effect(rule.get("effect", {}))
    _validate_effect(effect)

    rule_id = str(rule.get("id") or f"rule_{uuid.uuid4().hex[:12]}")
    status = str(rule.get("status", "active"))
    if status != "active":
        raise RuleChangeError("Only active mutable rules are supported in this version.")

    return {
        "id": rule_id,
        "title": title,
        "description": description,
        "type": rule_type,
        "status": status,
        "condition": condition,
        "effect": effect,
        "created_by": rule.get("created_by", player_id),
        "created_at": rule.get("created_at", utc_now()),
        "modified_by": rule.get("modified_by"),
        "modified_at": rule.get("modified_at"),
    }


def _find_rule(rules: list[dict[str, Any]], rule_id: str) -> dict[str, Any] | None:
    return next((rule for rule in rules if rule.get("id") == rule_id), None)


def normalize_effect(effect: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(effect, dict):
        raise RuleChangeError("Rule effect must be a JSON object.")
    normalized = {}
    for key, value in effect.items():
        normalized[EFFECT_ALIASES.get(key, key)] = value
    return normalized


def _validate_effect(effect: dict[str, Any]) -> None:
    supported = SUPPORTED_EFFECT_KEYS.intersection(effect)
    if not supported:
        raise RuleChangeError(
            "Mutable rules must include at least one supported mechanic effect: "
            f"{', '.join(sorted(SUPPORTED_EFFECT_KEYS))}."
        )
    for key in supported.intersection(INT_EFFECT_KEYS):
        value = _positive_int(effect[key], key)
        if key == "max_plays_per_turn" and value > 4:
            raise RuleChangeError("max_plays_per_turn cannot be greater than 4.")
        if key in {"draw_count", "draw_two_penalty", "wild_draw_four_penalty", "skip_penalty_cards", "reverse_penalty_cards"} and value > 10:
            raise RuleChangeError(f"{key} cannot be greater than 10.")
        if key == "win_hand_count" and value > 3:
            raise RuleChangeError("win_hand_count cannot be greater than 3.")
    for key in supported.intersection(BOOL_EFFECT_KEYS):
        _bool_value(effect[key], key)


def _validate_condition(condition: dict[str, Any]) -> None:
    if not isinstance(condition, dict):
        raise RuleChangeError("Rule condition must be a JSON object.")
    unknown = set(condition) - ALLOWED_CONDITION_KEYS
    if unknown:
        raise RuleChangeError(f"Unsupported condition key(s): {', '.join(sorted(unknown))}.")
    if "top_card" in condition:
        _validate_nested_keys(condition["top_card"], ALLOWED_CARD_CONDITION_KEYS, "top_card")
    if "current_player" in condition:
        _validate_nested_keys(condition["current_player"], ALLOWED_PLAYER_CONDITION_KEYS, "current_player")
    if "opponent" in condition:
        _validate_nested_keys(condition["opponent"], ALLOWED_PLAYER_CONDITION_KEYS, "opponent")


def _validate_nested_keys(value: Any, allowed: set[str], label: str) -> None:
    if not isinstance(value, dict):
        raise RuleChangeError(f"{label} condition must be a JSON object.")
    unknown = set(value) - allowed
    if unknown:
        raise RuleChangeError(f"Unsupported {label} condition key(s): {', '.join(sorted(unknown))}.")


def _positive_int(value: Any, field_name: str) -> int:
    if not isinstance(value, int) or value < 1:
        raise RuleChangeError(f"{field_name} must be a positive integer.")
    return value


def _bool_value(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise RuleChangeError(f"{field_name} must be a boolean.")
    return value


def _condition_applies(condition: dict[str, Any], context: dict[str, Any]) -> bool:
    if not condition:
        return True
    scope = condition.get("scope")
    if scope in {None, "all", "everyone"}:
        pass
    elif scope == "current_player" and condition.get("player_id") != context.get("player_id"):
        return False
    elif scope not in {"all", "everyone", "current_player"}:
        return False
    if "player_id" in condition and condition["player_id"] != context.get("player_id"):
        return False
    if "player_name" in condition and condition["player_name"] != context.get("player_name"):
        return False
    if "top_color" in condition and condition["top_color"] != context.get("top_color"):
        return False
    if "top_value" in condition and condition["top_value"] != context.get("top_value"):
        return False
    if "top_type" in condition and condition["top_type"] != context.get("top_type"):
        return False
    if "top_card" in condition and not _card_condition_applies(condition["top_card"], context):
        return False
    if "current_player" in condition and not _player_condition_applies(condition["current_player"], context, "current_player"):
        return False
    if "opponent" in condition and not _player_condition_applies(condition["opponent"], context, "opponent"):
        return False
    return True


def _card_condition_applies(condition: dict[str, Any], context: dict[str, Any]) -> bool:
    if "color" in condition and condition["color"] != context.get("top_color"):
        return False
    if "value" in condition and condition["value"] != context.get("top_value"):
        return False
    if "type" in condition and condition["type"] != context.get("top_type"):
        return False
    return True


def _player_condition_applies(condition: dict[str, Any], context: dict[str, Any], prefix: str) -> bool:
    if "id" in condition and condition["id"] != context.get(f"{prefix}_id"):
        return False
    if "name" in condition and condition["name"] != context.get(f"{prefix}_name"):
        return False
    if "hand_count" in condition and not _number_condition_applies(condition["hand_count"], context.get(f"{prefix}_hand_count")):
        return False
    return True


def _number_condition_applies(condition: Any, actual: int | None) -> bool:
    if actual is None:
        return False
    if isinstance(condition, int):
        return actual == condition
    if not isinstance(condition, dict):
        return False
    if "eq" in condition and actual != condition["eq"]:
        return False
    if "lt" in condition and actual >= condition["lt"]:
        return False
    if "lte" in condition and actual > condition["lte"]:
        return False
    if "gt" in condition and actual <= condition["gt"]:
        return False
    if "gte" in condition and actual < condition["gte"]:
        return False
    return True
