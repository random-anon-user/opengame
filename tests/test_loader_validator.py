from pathlib import Path

from opengame.loader import load_game
from opengame.validator import validate_game


SAMPLE_GAME = Path("content/sample_game")


def test_loads_sample_game() -> None:
    game = load_game(SAMPLE_GAME)

    assert game.title == "The Ember Path"
    assert game.start_scene == "crossroads"
    assert "brass_key" in game.items
    assert "open_ember_gate" in game.quests
    assert "gate_keeper" in game.npcs
    assert "crossroads" in game.scenes


def test_sample_game_validates() -> None:
    game = load_game(SAMPLE_GAME)

    assert validate_game(game) == []


def test_loads_nested_character_scene_folders(tmp_path: Path) -> None:
    story = tmp_path / "story"
    alice_scenes = story / "scenes" / "alice"
    shared_scenes = story / "scenes" / "shared"
    alice_scenes.mkdir(parents=True)
    shared_scenes.mkdir(parents=True)
    (story / "game.yaml").write_text(
        "id: nested\ntitle: Nested\nversion: 1\nstart_scene: alice_intro\n",
        encoding="utf-8",
    )
    (alice_scenes / "intro.yaml").write_text(
        "id: alice_intro\ntitle: Alice\ntext: Alice arrives.\nchoices:\n  - text: Meet Bob\n    target: shared_meeting\n",
        encoding="utf-8",
    )
    (shared_scenes / "meeting.yaml").write_text(
        "id: shared_meeting\ntitle: Meeting\ntext: Alice and Bob compare notes.\nending: true\nchoices: []\n",
        encoding="utf-8",
    )

    game = load_game(story)

    assert set(game.scenes) == {"alice_intro", "shared_meeting"}
    assert validate_game(game) == []


def test_validation_reports_missing_target(tmp_path: Path) -> None:
    story = tmp_path / "story"
    scenes = story / "scenes"
    scenes.mkdir(parents=True)
    (story / "game.yaml").write_text(
        "id: test\ntitle: Test\nversion: 1\nstart_scene: start\n",
        encoding="utf-8",
    )
    (scenes / "start.yaml").write_text(
        "id: start\ntitle: Start\ntext: Test\nchoices:\n  - text: Go\n    target: missing\n",
        encoding="utf-8",
    )

    issues = validate_game(load_game(story))

    assert len(issues) == 1
    assert "missing scene" in issues[0].message
