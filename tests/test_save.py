import json
from pathlib import Path

import pytest

from opengame.engine import GameEngine
from opengame.loader import load_game
from opengame.models import ContentError
from opengame.save import default_save_path, load_game_state, save_game_state


SAMPLE_GAME = Path("content/sample_game")


def test_save_round_trips_game_state(tmp_path: Path) -> None:
    game = load_game(SAMPLE_GAME)
    engine = GameEngine(game)
    engine.choose(1)
    engine.choose(1)

    save_path = tmp_path / "save.json"
    save_game_state(game, engine.state, save_path)
    restored = load_game_state(game, save_path)

    assert restored.current_scene == engine.state.current_scene
    assert restored.current_dialogue == engine.state.current_dialogue
    assert restored.flags == engine.state.flags
    assert restored.counters == engine.state.counters
    assert restored.inventory == engine.state.inventory
    assert restored.quests == engine.state.quests
    assert restored.relationships == engine.state.relationships


def test_load_rejects_save_for_different_game(tmp_path: Path) -> None:
    save_path = tmp_path / "save.json"
    save_path.write_text(
        json.dumps(
            {
                "format_version": 2,
                "game_id": "other_game",
                "game_version": 1,
                "state": {"current_scene": "crossroads"},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ContentError, match="different game"):
        load_game_state(load_game(SAMPLE_GAME), save_path)


def test_default_save_path_uses_game_pack_folder() -> None:
    game = load_game(SAMPLE_GAME)

    assert default_save_path(game) == SAMPLE_GAME / "save.json"
