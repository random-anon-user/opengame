from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from opengame.models import ContentError, GameData, GameState

SAVE_FORMAT_VERSION = 2


def default_save_path(game: GameData) -> Path:
    return (game.root or Path.cwd()) / "save.json"


def save_game_state(game: GameData, state: GameState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format_version": SAVE_FORMAT_VERSION,
        "game_id": game.id,
        "game_version": game.version,
        "state": {
            "current_scene": state.current_scene,
            "current_step_index": state.current_step_index,
            "current_dialogue": state.current_dialogue,
            "flags": state.flags,
            "counters": state.counters,
            "inventory": sorted(state.inventory),
            "quests": state.quests,
            "relationships": state.relationships,
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_game_state(game: GameData, path: Path) -> GameState:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ContentError(f"Save file does not exist: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ContentError(f"Save file is not valid JSON: {path}") from exc

    if not isinstance(payload, dict):
        raise ContentError(f"Save file must contain a JSON object: {path}")
    if payload.get("game_id") != game.id:
        raise ContentError(f"Save file belongs to a different game: {path}")
    if payload.get("format_version") != SAVE_FORMAT_VERSION:
        raise ContentError(f"Unsupported save format in {path}")

    state_data = _as_mapping(payload.get("state"), "state")
    current_scene = str(state_data.get("current_scene", ""))
    if current_scene not in game.scenes:
        raise ContentError(f"Save file points to missing scene '{current_scene}'")

    current_dialogue = state_data.get("current_dialogue")
    if current_dialogue is not None:
        current_dialogue = str(current_dialogue)
        _validate_dialogue(game, current_dialogue)

    flags = dict(game.flags)
    flags.update(_as_mapping(state_data.get("flags", {}), "flags"))

    counters = dict(game.counters)
    counters.update({str(key): int(value) for key, value in _as_mapping(state_data.get("counters", {}), "counters").items()})

    quests = {quest_id: quest.start_status for quest_id, quest in game.quests.items()}
    quests.update({str(key): str(value) for key, value in _as_mapping(state_data.get("quests", {}), "quests").items()})

    relationships = {npc_id: npc.relationship_start for npc_id, npc in game.npcs.items()}
    relationships.update(
        {str(key): int(value) for key, value in _as_mapping(state_data.get("relationships", {}), "relationships").items()}
    )

    inventory_data = state_data.get("inventory", [])
    if not isinstance(inventory_data, list):
        raise ContentError("Save field 'inventory' must be a list")

    return GameState(
        current_scene=current_scene,
        flags=flags,
        counters=counters,
        inventory={str(item_id) for item_id in inventory_data},
        quests=quests,
        relationships=relationships,
        current_dialogue=current_dialogue,
        current_step_index=int(state_data.get("current_step_index", 0)),
    )


def _as_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContentError(f"Save field '{field_name}' must be an object")
    return value


def _validate_dialogue(game: GameData, dialogue_ref: str) -> None:
    if ":" not in dialogue_ref:
        raise ContentError(f"Save file has invalid dialogue reference '{dialogue_ref}'")
    npc_id, dialogue_id = dialogue_ref.split(":", 1)
    if npc_id not in game.npcs or dialogue_id not in game.npcs[npc_id].dialogues:
        raise ContentError(f"Save file points to missing dialogue '{dialogue_ref}'")
