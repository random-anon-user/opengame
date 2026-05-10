from pathlib import Path

from opengame.engine import GameEngine
from opengame.loader import load_game
from opengame.models import Condition


SAMPLE_GAME = Path("content/sample_game")


def test_choice_effects_update_state_and_move_scene() -> None:
    engine = GameEngine(load_game(SAMPLE_GAME))

    engine.choose(1)
    engine.choose(1)

    assert engine.state.current_scene == "crossroads"
    assert "brass_key" in engine.state.inventory
    assert "lantern" in engine.state.inventory
    assert engine.state.flags["found_lantern"] is True
    assert engine.state.counters["courage"] == 2


def test_conditions_hide_unavailable_choices() -> None:
    engine = GameEngine(load_game(SAMPLE_GAME))
    engine.choose(2)

    choices = [choice.text for choice in engine.visible_choices()]

    assert "Unlock the gate with the brass key" not in choices


def test_can_reach_sample_ending() -> None:
    engine = GameEngine(load_game(SAMPLE_GAME))

    engine.choose(1)
    engine.choose(1)
    engine.choose(2)
    engine.choose(1)

    assert engine.scene.id == "gate_open"
    assert engine.scene.ending is True
    assert engine.state.quests["open_ember_gate"] == "completed"


def test_quest_status_conditions_can_gate_choices() -> None:
    engine = GameEngine(load_game(SAMPLE_GAME))

    assert engine.condition_met(Condition("quest_status", "open_ember_gate", "active")) is True
    assert engine.state.quests["open_ember_gate"] == "active"


def test_scene_choice_can_enter_npc_dialogue() -> None:
    engine = GameEngine(load_game(SAMPLE_GAME))

    engine.choose(2)
    engine.choose(1)

    assert engine.dialogue is not None
    assert engine.state.current_dialogue == "gate_keeper:greeting"


def test_dialogue_can_change_relationship_and_unlock_branch() -> None:
    engine = GameEngine(load_game(SAMPLE_GAME))

    engine.choose(2)
    engine.choose(1)
    engine.choose(1)

    assert engine.state.current_dialogue == "gate_keeper:ember_road"
    assert engine.state.relationships["gate_keeper"] == 1
    choices = [choice.text for choice in engine.visible_choices()]
    assert "Ask for the hidden name of the key" in choices


def test_dialogue_can_return_to_scene_and_start_quest() -> None:
    engine = GameEngine(load_game(SAMPLE_GAME))

    engine.choose(2)
    engine.choose(1)
    engine.choose(1)
    engine.choose(1)

    assert engine.dialogue is None
    assert engine.scene.id == "gate"
    assert engine.state.flags["met_keeper"] is True
    assert engine.state.quests["open_ember_gate"] == "active"
