from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from opengame.models import Choice, Condition, ContentError, DialogueNode, Effect, GameData, Item, NPC, Quest, Scene, Step, StepOption


def load_game(root: str | Path) -> GameData:
    """Load a modular YAML story pack from a directory."""
    root_path = Path(root)
    if not root_path.exists() or not root_path.is_dir():
        raise ContentError(f"Story pack directory does not exist: {root_path}")

    meta = _read_yaml(root_path / "game.yaml")
    variables = _read_yaml(root_path / "variables.yaml", optional=True)
    items_data = _read_yaml(root_path / "items.yaml", optional=True)
    quests_data = _read_yaml(root_path / "quests.yaml", optional=True)
    npcs_data = _read_yaml(root_path / "npcs.yaml", optional=True)

    scenes_dir = root_path / "arcs"
    if not scenes_dir.exists():
        scenes_dir = root_path / "scenes"
    if not scenes_dir.exists():
        raise ContentError(f"Missing arcs or scenes directory: {root_path}")

    scenes: dict[str, Scene] = {}
    for scene_file in sorted(scenes_dir.rglob("*.yaml")):
        for scene in _load_scenes_from_file(scene_file):
            if scene.id in scenes:
                raise ContentError(f"Duplicate scene id '{scene.id}' in {scene_file}")
            scenes[scene.id] = scene

    items: dict[str, Item] = {}
    for item_data in _as_list(items_data.get("items", []), "items"):
        item = _parse_item(item_data)
        if item.id in items:
            raise ContentError(f"Duplicate item id '{item.id}'")
        items[item.id] = item

    quests: dict[str, Quest] = {}
    for quest_data in _as_list(quests_data.get("quests", []), "quests"):
        quest = _parse_quest(quest_data)
        if quest.id in quests:
            raise ContentError(f"Duplicate quest id '{quest.id}'")
        quests[quest.id] = quest

    npcs: dict[str, NPC] = {}
    for npc_data in _as_list(npcs_data.get("npcs", []), "npcs"):
        npc = _parse_npc(npc_data)
        if npc.id in npcs:
            raise ContentError(f"Duplicate NPC id '{npc.id}'")
        npcs[npc.id] = npc

    try:
        return GameData(
            id=str(meta["id"]),
            title=str(meta["title"]),
            version=int(meta.get("version", 1)),
            start_scene=str(meta["start_scene"]),
            author=str(meta.get("author", "")),
            description=str(meta.get("description", "")),
            scenes=scenes,
            items=items,
            quests=quests,
            npcs=npcs,
            flags=dict(variables.get("flags", {})),
            counters={key: int(value) for key, value in variables.get("counters", {}).items()},
            root=root_path,
        )
    except KeyError as exc:
        raise ContentError(f"Missing required game metadata key: {exc.args[0]}") from exc


def _load_scenes_from_file(path: Path) -> list[Scene]:
    """Load one or more scenes from a YAML file.

    The file may contain a single scene mapping or a list of scene mappings.
    """
    if not path.exists():
        raise ContentError(f"Missing scene file: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except yaml.YAMLError as exc:
        raise ContentError(f"Invalid YAML in {path}: {exc}") from exc

    if data is None:
        raise ContentError(f"Empty scene file: {path}")
    if isinstance(data, list):
        return [_parse_scene(item, path) for item in data]
    if isinstance(data, dict):
        return [_parse_scene(data, path)]
    raise ContentError(f"Expected a mapping or list of mappings in {path}")


def _read_yaml(path: Path, optional: bool = False) -> dict[str, Any]:
    if optional and not path.exists():
        return {}
    if not path.exists():
        raise ContentError(f"Missing required YAML file: {path}")

    try:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
    except yaml.YAMLError as exc:
        raise ContentError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ContentError(f"Expected a YAML mapping in {path}")
    return data


def _parse_scene(data: dict[str, Any], source: Path) -> Scene:
    try:
        steps_data = data.get("steps")
        if steps_data is not None:
            steps = tuple(_parse_step(step, source) for step in _as_list(steps_data, "steps"))
            return Scene(
                id=str(data["id"]),
                title=str(data.get("title", data["id"])),
                text="",
                ending=bool(data.get("ending", False)),
                source=source,
                steps=steps,
            )

        choices = tuple(_parse_choice(choice) for choice in _as_list(data.get("choices", []), "choices"))
        return Scene(
            id=str(data["id"]),
            title=str(data.get("title", data["id"])),
            text=str(data["text"]),
            choices=choices,
            ending=bool(data.get("ending", False)),
            source=source,
        )
    except KeyError as exc:
        raise ContentError(f"Missing required scene key '{exc.args[0]}' in {source}") from exc


def _parse_step(data: dict[str, Any], source: Path) -> Step:
    if not isinstance(data, dict):
        raise ContentError("Each step must be a mapping")

    text = str(data.get("text", ""))
    author = str(data["author"]) if "author" in data else None
    next_scene = str(data["next"]) if "next" in data else None

    options_data = data.get("options")
    if options_data is not None and "next" in data:
        raise ContentError(f"Step with options cannot also have a direct 'next' in {source}")
    if next_scene and "options" in data:
        raise ContentError(f"Step with 'next' cannot also have options in {source}")

    options: list[StepOption] = []
    if options_data is not None:
        for opt_data in _as_list(options_data, "options"):
            options.append(_parse_step_option(opt_data, source))

    return Step(text=text, author=author, options=tuple(options), next_scene=next_scene)


def _parse_step_option(data: dict[str, Any], source: Path) -> StepOption:
    if not isinstance(data, dict):
        raise ContentError("Each option must be a mapping")

    opt_text = str(data["text"])
    next_scene = str(data["next"]) if "next" in data else None
    response_data = data.get("response")

    conditions = tuple(_parse_condition(item) for item in _as_list(data.get("conditions", []), "conditions"))
    effects = tuple(_parse_effect(item) for item in _as_list(data.get("effects", []), "effects"))

    response = ()
    if response_data is not None:
        if isinstance(response_data, list):
            response = tuple(_parse_step(s, source) for s in response_data)
        elif isinstance(response_data, dict):
            response = (_parse_step(response_data, source),)
        else:
            response = (_parse_step({"text": str(response_data)}, source),)

    return StepOption(
        text=opt_text,
        next_scene=next_scene,
        responses=response,
        conditions=conditions,
        effects=effects,
    )


def _parse_choice(data: Any, context_npc: str | None = None) -> Choice:
    if not isinstance(data, dict):
        raise ContentError("Each choice must be a mapping")
    if "target" not in data and "dialogue" not in data:
        raise ContentError("Each choice must define either 'target' or 'dialogue'")
    if "target" in data and "dialogue" in data:
        raise ContentError("A choice cannot define both 'target' and 'dialogue'")

    dialogue = data.get("dialogue")
    if dialogue is not None:
        dialogue = str(dialogue)
        if context_npc and ":" not in dialogue:
            dialogue = f"{context_npc}:{dialogue}"

    try:
        return Choice(
            text=str(data["text"]),
            target=str(data["target"]) if "target" in data else None,
            dialogue=dialogue,
            conditions=tuple(_parse_condition(item) for item in _as_list(data.get("conditions", []), "conditions")),
            effects=tuple(_parse_effect(item) for item in _as_list(data.get("effects", []), "effects")),
        )
    except KeyError as exc:
        raise ContentError(f"Missing required choice key: {exc.args[0]}") from exc


def _parse_condition(data: Any) -> Condition:
    if not isinstance(data, dict):
        raise ContentError("Each condition must be a mapping")
    equals = data.get("equals", True)

    if "flag" in data:
        return Condition("flag", str(data["flag"]), equals)
    if "counter" in data:
        return Condition("counter", str(data["counter"]), equals)
    if "has_item" in data:
        return Condition("has_item", str(data["has_item"]), equals)
    if "quest_status" in data:
        payload = _as_mapping(data["quest_status"], "quest_status condition")
        return Condition("quest_status", str(payload["quest"]), payload.get("equals", equals))
    if "relationship" in data:
        payload = _as_mapping(data["relationship"], "relationship condition")
        return Condition("relationship", str(payload["npc"]), int(payload["at_least"]))

    raise ContentError(f"Unknown condition format: {data}")


def _parse_effect(data: Any) -> Effect:
    if not isinstance(data, dict):
        raise ContentError("Each effect must be a mapping")

    if "set" in data:
        payload = _as_mapping(data["set"], "set effect")
        return Effect("set_flag", str(payload["flag"]), payload.get("value", True))
    if "increment" in data:
        payload = _as_mapping(data["increment"], "increment effect")
        return Effect("increment_counter", str(payload["counter"]), int(payload.get("amount", 1)))
    if "kind" in data:
        kind = data["kind"]
        if kind == "set_flag":
            return Effect("set_flag", str(data["key"]), data.get("value", True))
        elif kind == "increment_counter":
            return Effect("increment_counter", str(data["key"]), int(data.get("value", 1)))
    if "add_item" in data:
        return Effect("add_item", str(data["add_item"]))
    if "remove_item" in data:
        return Effect("remove_item", str(data["remove_item"]))
    if "start_quest" in data:
        return Effect("set_quest_status", str(data["start_quest"]), "active")
    if "complete_quest" in data:
        return Effect("set_quest_status", str(data["complete_quest"]), "completed")
    if "fail_quest" in data:
        return Effect("set_quest_status", str(data["fail_quest"]), "failed")
    if "set_quest_status" in data:
        payload = _as_mapping(data["set_quest_status"], "set_quest_status effect")
        return Effect("set_quest_status", str(payload["quest"]), str(payload["status"]))
    if "change_relationship" in data:
        payload = _as_mapping(data["change_relationship"], "change_relationship effect")
        return Effect("change_relationship", str(payload["npc"]), int(payload.get("amount", 0)))
    if "set_relationship" in data:
        payload = _as_mapping(data["set_relationship"], "set_relationship effect")
        return Effect("set_relationship", str(payload["npc"]), int(payload["value"]))

    raise ContentError(f"Unknown effect format: {data}")


def _parse_item(data: Any) -> Item:
    if not isinstance(data, dict):
        raise ContentError("Each item must be a mapping")
    try:
        return Item(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data.get("description", "")),
        )
    except KeyError as exc:
        raise ContentError(f"Missing required item key: {exc.args[0]}") from exc


def _parse_quest(data: Any) -> Quest:
    if not isinstance(data, dict):
        raise ContentError("Each quest must be a mapping")
    try:
        return Quest(
            id=str(data["id"]),
            title=str(data["title"]),
            description=str(data.get("description", "")),
            start_status=str(data.get("start_status", "inactive")),
        )
    except KeyError as exc:
        raise ContentError(f"Missing required quest key: {exc.args[0]}") from exc


def _parse_npc(data: Any) -> NPC:
    if not isinstance(data, dict):
        raise ContentError("Each NPC must be a mapping")
    try:
        npc_id = str(data["id"])
        dialogues: dict[str, DialogueNode] = {}
        for dialogue_data in _as_list(data.get("dialogues", []), "dialogues"):
            dialogue = _parse_dialogue(dialogue_data, npc_id)
            if dialogue.id in dialogues:
                raise ContentError(f"Duplicate dialogue id '{dialogue.id}' for NPC '{npc_id}'")
            dialogues[dialogue.id] = dialogue

        return NPC(
            id=npc_id,
            name=str(data["name"]),
            description=str(data.get("description", "")),
            relationship_start=int(data.get("relationship_start", 0)),
            dialogues=dialogues,
        )
    except KeyError as exc:
        raise ContentError(f"Missing required NPC key: {exc.args[0]}") from exc


def _parse_dialogue(data: Any, npc_id: str) -> DialogueNode:
    if not isinstance(data, dict):
        raise ContentError("Each dialogue node must be a mapping")
    try:
        return DialogueNode(
            id=str(data["id"]),
            title=str(data.get("title", data["id"])),
            text=str(data["text"]),
            choices=tuple(_parse_choice(choice, npc_id) for choice in _as_list(data.get("choices", []), "choices")),
        )
    except KeyError as exc:
        raise ContentError(f"Missing required dialogue key '{exc.args[0]}' for NPC '{npc_id}'") from exc


def _as_list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ContentError(f"Expected '{label}' to be a list")
    return value


def _as_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ContentError(f"Expected '{label}' to be a mapping")
    return value
