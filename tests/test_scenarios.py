"""Tests for the scenario definitions and the instruction builder."""
import pytest

from app.scenarios import SCENARIOS, build_instructions, get_voice


@pytest.mark.parametrize("key", SCENARIOS)
def test_every_scenario_is_complete(key):
    scenario = SCENARIOS[key]
    assert scenario["persona"].strip()
    assert scenario["goal"].strip()
    assert scenario["voice"].strip()


@pytest.mark.parametrize("key", SCENARIOS)
def test_instructions_carry_the_persona_goal_and_guard_rails(key):
    instructions = build_instructions(key)
    assert SCENARIOS[key]["persona"] in instructions
    assert SCENARIOS[key]["goal"] in instructions
    assert "Speak ONLY English" in instructions
    assert "Never repeat the same sentence twice" in instructions


def test_unknown_scenario_falls_back_to_the_default():
    assert build_instructions("nope") == build_instructions("schedule_simple")
    assert get_voice("nope", default="marin") == "marin"
