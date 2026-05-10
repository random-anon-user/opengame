from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ContentError(Exception):
    """Raised when a story pack cannot be loaded or validated."""


@dataclass(frozen=True)
class Condition:
    kind: str
    key: str
    equals: Any = True


@dataclass(frozen=True)
class Effect:
    kind: str
    key: str
    value: Any = None


@dataclass(frozen=True)
class Choice:
    text: str
    target: str | None = None
    dialogue: str | None = None
    conditions: tuple[Condition, ...] = ()
    effects: tuple[Effect, ...] = ()


@dataclass(frozen=True)
class StepOption:
    text: str
    next_scene: str | None = None
    responses: tuple[Step, ...] = ()
    conditions: tuple[Condition, ...] = ()
    effects: tuple[Effect, ...] = ()


@dataclass(frozen=True)
class Step:
    text: str
    author: str | None = None
    options: tuple[StepOption, ...] = ()
    next_scene: str | None = None


@dataclass(frozen=True)
class Scene:
    id: str
    title: str
    text: str
    choices: tuple[Choice, ...] = ()
    ending: bool = False
    source: Path | None = None
    steps: tuple[Step, ...] = ()

    @property
    def has_steps(self) -> bool:
        return len(self.steps) > 0


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    description: str = ""


@dataclass(frozen=True)
class Quest:
    id: str
    title: str
    description: str
    start_status: str = "inactive"


@dataclass(frozen=True)
class DialogueNode:
    id: str
    title: str
    text: str
    choices: tuple[Choice, ...] = ()


@dataclass(frozen=True)
class NPC:
    id: str
    name: str
    description: str = ""
    relationship_start: int = 0
    dialogues: dict[str, DialogueNode] = field(default_factory=dict)


@dataclass(frozen=True)
class GameData:
    id: str
    title: str
    version: int
    start_scene: str
    author: str
    description: str
    scenes: dict[str, Scene]
    items: dict[str, Item] = field(default_factory=dict)
    quests: dict[str, Quest] = field(default_factory=dict)
    npcs: dict[str, NPC] = field(default_factory=dict)
    flags: dict[str, Any] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=dict)
    root: Path | None = None


@dataclass
class GameState:
    current_scene: str
    flags: dict[str, Any]
    counters: dict[str, int]
    inventory: set[str] = field(default_factory=set)
    quests: dict[str, str] = field(default_factory=dict)
    relationships: dict[str, int] = field(default_factory=dict)
    current_dialogue: str | None = None
    current_step_index: int = 0

    @classmethod
    def from_game(cls, game: GameData) -> GameState:
        return cls(
            current_scene=game.start_scene,
            flags=dict(game.flags),
            counters=dict(game.counters),
            quests={quest_id: quest.start_status for quest_id, quest in game.quests.items()},
            relationships={npc_id: npc.relationship_start for npc_id, npc in game.npcs.items()},
        )
