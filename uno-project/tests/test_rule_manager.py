import pytest

from uno_api.rule_manager import (
    RuleChangeError,
    add_mutable_rule,
    combined_rules,
    default_mutable_rules,
    modify_mutable_rule,
    remove_mutable_rule,
    rule_mechanics,
)


def sample_rule():
    return {
        "id": "bonus_red_7",
        "title": "Bonus Red Seven",
        "description": "Players may play two cards per turn.",
        "type": "turn_modifier",
        "condition": {"scope": "all"},
        "effect": {"max_plays_per_turn": 2},
    }


def test_add_mutable_rule_increments_version_and_tracks_creator():
    rules = add_mutable_rule(default_mutable_rules(), "p1", sample_rule())

    assert rules["version"] == 2
    assert rules["rules"][0]["id"] == "bonus_red_7"
    assert rules["rules"][0]["created_by"] == "p1"


def test_add_mutable_rule_rejects_missing_description():
    rule = sample_rule()
    rule["description"] = ""

    with pytest.raises(RuleChangeError):
        add_mutable_rule(default_mutable_rules(), "p1", rule)


def test_modify_mutable_rule_updates_allowed_fields():
    rules = add_mutable_rule(default_mutable_rules(), "p1", sample_rule())

    modified = modify_mutable_rule(rules, "p2", "bonus_red_7", {"description": "Changed rule."})

    assert modified["rules"][0]["description"] == "Changed rule."
    assert modified["rules"][0]["modified_by"] == "p2"


def test_remove_mutable_rule_removes_rule_and_records_last_removed():
    rules = add_mutable_rule(default_mutable_rules(), "p1", sample_rule())

    removed = remove_mutable_rule(rules, "p2", "bonus_red_7")

    assert removed["rules"] == []
    assert removed["last_removed_rule"]["id"] == "bonus_red_7"


def test_combined_rules_separates_base_and_mutable_layers():
    combined = combined_rules(default_mutable_rules())

    assert "base_rules" in combined
    assert "mutable_rules" in combined
    assert "immutable" in combined["note"]


def test_rule_mechanics_applies_active_mutable_effects():
    rules = add_mutable_rule(default_mutable_rules(), "p1", sample_rule())

    mechanics = rule_mechanics(rules)

    assert mechanics["max_plays_per_turn"] == 2
    assert mechanics["active_rule_ids"] == ["bonus_red_7"]


def test_add_mutable_rule_rejects_non_mechanical_effect():
    rule = sample_rule()
    rule["effect"] = {"flavor_text": "This should not be accepted."}

    with pytest.raises(RuleChangeError):
        add_mutable_rule(default_mutable_rules(), "p1", rule)


def test_rule_mechanics_supports_nested_top_card_condition():
    rule = sample_rule()
    rule["condition"] = {"top_card": {"color": "red", "type": "number"}}
    rules = add_mutable_rule(default_mutable_rules(), "p1", rule)

    assert rule_mechanics(rules, {"top_color": "red", "top_type": "number"})["max_plays_per_turn"] == 2
    assert rule_mechanics(rules, {"top_color": "blue", "top_type": "number"})["max_plays_per_turn"] == 1


def test_rule_mechanics_supports_player_hand_count_condition():
    rule = sample_rule()
    rule["condition"] = {"current_player": {"hand_count": {"lte": 2}}}
    rules = add_mutable_rule(default_mutable_rules(), "p1", rule)

    assert rule_mechanics(rules, {"current_player_hand_count": 2})["max_plays_per_turn"] == 2
    assert rule_mechanics(rules, {"current_player_hand_count": 3})["max_plays_per_turn"] == 1


def test_rule_mechanics_supports_boolean_matching_effects():
    rule = sample_rule()
    rule["effect"] = {"allow_same_type_match": True}
    rules = add_mutable_rule(default_mutable_rules(), "p1", rule)

    assert rule_mechanics(rules)["allow_same_type_match"] is True
