from __future__ import annotations

from dataclasses import dataclass

from opengame.models import GameData

VALID_QUEST_STATUSES = {"inactive", "active", "completed", "failed"}


@dataclass(frozen=True)
class ValidationIssue:
    message: str
    scene_id: str | None = None


def validate_game(game: GameData) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if game.start_scene not in game.scenes:
        issues.append(ValidationIssue(f"Start scene '{game.start_scene}' does not exist"))

    for quest in game.quests.values():
        if quest.start_status not in VALID_QUEST_STATUSES:
            issues.append(
                ValidationIssue(
                    f"Quest '{quest.id}' has invalid start_status '{quest.start_status}'",
                )
            )

    for scene in game.scenes.values():
        if scene.has_steps:
            issues.extend(_validate_stepped_scene(game, scene))
        else:
            issues.extend(_validate_flat_scene(game, scene))

    return issues


def _validate_flat_scene(game: GameData, scene) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if scene.ending and scene.choices:
        issues.append(ValidationIssue("Ending scenes should not define choices", scene.id))

    if not scene.ending and not scene.choices:
        issues.append(ValidationIssue("Non-ending scene has no choices", scene.id))

    for choice in scene.choices:
        issues.extend(_validate_choice(game, choice, scene.id))

    return issues


def _validate_stepped_scene(game: GameData, scene) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if scene.ending:
        issues.append(ValidationIssue("Stepped scenes should not be marked as ending", scene.id))

    if not scene.steps:
        issues.append(ValidationIssue("Stepped scene has no steps", scene.id))
        return issues

    for i, step in enumerate(scene.steps):
        step_id = f"{scene.id}:step[{i}]"

        if step.next_scene and step.options:
            issues.append(ValidationIssue(
                f"Step has both options and a direct 'next' — only one is allowed", step_id
            ))

        if step.next_scene and step.next_scene not in game.scenes:
            issues.append(ValidationIssue(
                f"Step 'next' targets missing scene '{step.next_scene}'", step_id
            ))

        for j, opt in enumerate(step.options):
            opt_id = f"{step_id}:option[{j}]"

            if opt.next_scene and opt.next_scene not in game.scenes:
                issues.append(ValidationIssue(
                    f"Option 'next' targets missing scene '{opt.next_scene}'", opt_id
                ))

            for condition in opt.conditions:
                issues.extend(_validate_condition(game, condition, opt_id))

            for effect in opt.effects:
                issues.extend(_validate_effect(game, effect, opt_id))

            for k, resp in enumerate(opt.responses):
                resp_id = f"{opt_id}:response[{k}]"
                if resp.next_scene and resp.next_scene not in game.scenes:
                    issues.append(ValidationIssue(
                        f"Response 'next' targets missing scene '{resp.next_scene}'", resp_id
                    ))

    return issues


def _validate_choice(game: GameData, choice, source_id: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if choice.target is None and choice.dialogue is None:
        issues.append(ValidationIssue(f"Choice '{choice.text}' has no destination", source_id))

    if choice.target is not None and choice.target not in game.scenes:
        issues.append(
            ValidationIssue(
                f"Choice '{choice.text}' targets missing scene '{choice.target}'",
                source_id,
            )
        )

    if choice.dialogue is not None and not _dialogue_exists(game, choice.dialogue):
        issues.append(
            ValidationIssue(
                f"Choice '{choice.text}' targets missing dialogue '{choice.dialogue}'",
                source_id,
            )
        )

    for condition in choice.conditions:
        issues.extend(_validate_condition(game, condition, source_id))

    for effect in choice.effects:
        issues.extend(_validate_effect(game, effect, source_id))

    return issues


def _validate_condition(game: GameData, condition, source_id: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if condition.kind == "flag" and condition.key not in game.flags:
        issues.append(ValidationIssue(f"Condition references unknown flag '{condition.key}'", source_id))
    if condition.kind == "counter" and condition.key not in game.counters:
        issues.append(ValidationIssue(f"Condition references unknown counter '{condition.key}'", source_id))
    if condition.kind == "has_item" and condition.key not in game.items:
        issues.append(ValidationIssue(f"Condition references unknown item '{condition.key}'", source_id))
    if condition.kind == "quest_status":
        if condition.key not in game.quests:
            issues.append(ValidationIssue(f"Condition references unknown quest '{condition.key}'", source_id))
        if condition.equals not in VALID_QUEST_STATUSES:
            issues.append(ValidationIssue(f"Condition references invalid quest status '{condition.equals}'", source_id))
    if condition.kind == "relationship" and condition.key not in game.npcs:
        issues.append(ValidationIssue(f"Condition references unknown NPC '{condition.key}'", source_id))

    return issues


def _validate_effect(game: GameData, effect, source_id: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    if effect.kind == "set_flag" and effect.key not in game.flags:
        issues.append(ValidationIssue(f"Effect references unknown flag '{effect.key}'", source_id))
    if effect.kind == "increment_counter" and effect.key not in game.counters:
        issues.append(ValidationIssue(f"Effect references unknown counter '{effect.key}'", source_id))
    if effect.kind in {"add_item", "remove_item"} and effect.key not in game.items:
        issues.append(ValidationIssue(f"Effect references unknown item '{effect.key}'", source_id))
    if effect.kind == "set_quest_status":
        if effect.key not in game.quests:
            issues.append(ValidationIssue(f"Effect references unknown quest '{effect.key}'", source_id))
        if effect.value not in VALID_QUEST_STATUSES:
            issues.append(ValidationIssue(f"Effect references invalid quest status '{effect.value}'", source_id))
    if effect.kind in {"change_relationship", "set_relationship"} and effect.key not in game.npcs:
        issues.append(ValidationIssue(f"Effect references unknown NPC '{effect.key}'", source_id))

    return issues


def _dialogue_exists(game: GameData, dialogue_ref: str) -> bool:
    if ":" not in dialogue_ref:
        return False
    npc_id, dialogue_id = dialogue_ref.split(":", 1)
    return npc_id in game.npcs and dialogue_id in game.npcs[npc_id].dialogues
