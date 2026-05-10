from __future__ import annotations

from collections.abc import Sequence

from opengame.models import (
    Choice,
    Condition,
    ContentError,
    DialogueNode,
    Effect,
    GameData,
    GameState,
    Scene,
    Step,
    StepOption,
)


class GameEngine:
    def __init__(self, game: GameData, state: GameState | None = None) -> None:
        self.game = game
        self.state = state or GameState.from_game(game)
        self._pending_responses: list[Step] = []
        self._pending_next_scene: str | None = None
        self._step_option_map: dict[int, int] = {}  # choice_index -> step option_index

    @property
    def scene(self) -> Scene:
        try:
            return self.game.scenes[self.state.current_scene]
        except KeyError as exc:
            raise ContentError(f"Runtime state points to missing scene '{self.state.current_scene}'") from exc

    @property
    def dialogue(self) -> DialogueNode | None:
        if self.state.current_dialogue is None:
            return None

        npc_id, dialogue_id = self._split_dialogue_ref(self.state.current_dialogue)
        try:
            return self.game.npcs[npc_id].dialogues[dialogue_id]
        except KeyError as exc:
            raise ContentError(f"Runtime state points to missing dialogue '{self.state.current_dialogue}'") from exc

    @property
    def current_step(self) -> Step | None:
        """Return the active step (pending response or current scene step), or None."""
        if self._pending_responses:
            return self._pending_responses[0]
        if self.scene.has_steps:
            steps = self.scene.steps
            if self.state.current_step_index < len(steps):
                return steps[self.state.current_step_index]
        return None

    def visible_choices(self) -> list[Choice]:
        self._step_option_map.clear()

        if self.dialogue:
            return [choice for choice in self.dialogue.choices if self.conditions_met(choice.conditions)]

        if self._pending_responses:
            return [Choice(text="Next", target=None)]

        if self.scene.has_steps:
            step = self.current_step
            if step is None:
                return []

            if step.next_scene:
                return []  # will be handled by _auto_advance

            if step.options:
                visible: list[Choice] = []
                choice_index = 0
                for i, opt in enumerate(step.options):
                    if self.conditions_met(opt.conditions):
                        self._step_option_map[choice_index] = i
                        visible.append(Choice(text=opt.text, target=None))
                        choice_index += 1
                return visible

            return [Choice(text="Next", target=None)]

        return [choice for choice in self.scene.choices if self.conditions_met(choice.conditions)]

    def current_choices(self) -> tuple[Choice, ...]:
        dialogue = self.dialogue
        if dialogue:
            return dialogue.choices
        return self.scene.choices

    def conditions_met(self, conditions: Sequence[Condition]) -> bool:
        return all(self.condition_met(condition) for condition in conditions)

    def condition_met(self, condition: Condition) -> bool:
        actual = self._condition_value(condition)
        if condition.kind == "relationship":
            return int(actual) >= int(condition.equals)
        return actual == condition.equals

    def choose(self, choice_number: int) -> Scene | DialogueNode:
        if self.dialogue:
            return self._choose_dialogue(choice_number)

        if self._pending_responses:
            return self._advance_response()

        return self._choose_scene(choice_number)

    def _choose_dialogue(self, choice_number: int) -> Scene | DialogueNode:
        choices = [choice for choice in self.dialogue.choices if self.conditions_met(choice.conditions)]
        if choice_number < 1 or choice_number > len(choices):
            raise ValueError(f"Choice must be between 1 and {len(choices)}")

        choice = choices[choice_number - 1]
        self.apply_effects(choice.effects)
        if choice.dialogue:
            self.state.current_dialogue = choice.dialogue
            return self.dialogue_or_error()
        if choice.target:
            self.state.current_dialogue = None
            self.state.current_scene = choice.target
            return self.scene
        raise ContentError(f"Dialogue choice '{choice.text}' has no destination")

    def _choose_scene(self, choice_number: int) -> Scene | DialogueNode:
        scene = self.scene

        if scene.has_steps:
            choices = self.visible_choices()

            if not choices:
                raise ValueError("No choices available to advance the scene")

            if choice_number < 1 or choice_number > len(choices):
                raise ValueError(f"Choice must be between 1 and {len(choices)}")

            choice_index = choice_number - 1

            if choice_index in self._step_option_map:
                return self._handle_step_option(choice_index)

            choice = choices[choice_index]
            if choice.text == "Next":
                self.state.current_step_index += 1
                self._auto_advance()
                return self.scene

            raise ContentError(f"Unknown choice type in stepped scene: '{choice.text}'")

        choices = self.visible_choices()
        if choice_number < 1 or choice_number > len(choices):
            raise ValueError(f"Choice must be between 1 and {len(choices)}")

        choice = choices[choice_number - 1]
        self.apply_effects(choice.effects)
        if choice.dialogue:
            self.state.current_dialogue = choice.dialogue
            return self.dialogue_or_error()
        if choice.target:
            self.state.current_dialogue = None
            self.state.current_scene = choice.target
            return self.scene
        raise ContentError(f"Choice '{choice.text}' has no destination")

    def _handle_step_option(self, choice_index: int) -> Scene:
        step = self.current_step
        if step is None:
            raise ContentError("No current step available")

        opt_index = self._step_option_map[choice_index]
        option = step.options[opt_index]

        self.apply_effects(option.effects)

        if option.responses:
            self._pending_responses = list(option.responses)
            self._pending_next_scene = option.next_scene
            return self.scene

        if option.next_scene:
            self.state.current_step_index = 0
            self.state.current_scene = option.next_scene
            return self.scene

        self.state.current_step_index += 1
        self._auto_advance()
        return self.scene

    def _advance_response(self) -> Scene:
        self._pending_responses.pop(0)

        if self._pending_responses:
            return self.scene

        next_scene = self._pending_next_scene
        self._pending_next_scene = None

        if next_scene:
            self.state.current_step_index = 0
            self.state.current_scene = next_scene
            return self.scene

        self.state.current_step_index += 1
        self._auto_advance()
        return self.scene

    def _auto_advance(self) -> None:
        """Automatically advance past steps with direct next_scene."""
        while True:
            step = self.current_step
            if step is None:
                return
            if step.next_scene:
                self.state.current_step_index = 0
                self.state.current_scene = step.next_scene
                return
            if step.options or step.text:
                return
            self.state.current_step_index += 1

    def apply_effects(self, effects: Sequence[Effect]) -> None:
        for effect in effects:
            if effect.kind == "set_flag":
                self.state.flags[effect.key] = effect.value
            elif effect.kind == "increment_counter":
                self.state.counters[effect.key] = self.state.counters.get(effect.key, 0) + int(effect.value)
            elif effect.kind == "add_item":
                self.state.inventory.add(effect.key)
            elif effect.kind == "remove_item":
                self.state.inventory.discard(effect.key)
            elif effect.kind == "set_quest_status":
                self.state.quests[effect.key] = str(effect.value)
            elif effect.kind == "change_relationship":
                self.state.relationships[effect.key] = self.state.relationships.get(effect.key, 0) + int(effect.value)
            elif effect.kind == "set_relationship":
                self.state.relationships[effect.key] = int(effect.value)
            else:
                raise ContentError(f"Unknown effect kind '{effect.kind}'")

    def _condition_value(self, condition: Condition) -> object:
        if condition.kind == "flag":
            return self.state.flags.get(condition.key, False)
        if condition.kind == "counter":
            return self.state.counters.get(condition.key, 0)
        if condition.kind == "has_item":
            return condition.key in self.state.inventory
        if condition.kind == "quest_status":
            return self.state.quests.get(condition.key, "inactive")
        if condition.kind == "relationship":
            return self.state.relationships.get(condition.key, 0)
        raise ContentError(f"Unknown condition kind '{condition.kind}'")

    def dialogue_or_error(self) -> DialogueNode:
        dialogue = self.dialogue
        if dialogue is None:
            raise ContentError("Runtime state is not in dialogue")
        return dialogue

    def _split_dialogue_ref(self, dialogue_ref: str) -> tuple[str, str]:
        if ":" not in dialogue_ref:
            raise ContentError(f"Dialogue reference must use 'npc_id:dialogue_id': {dialogue_ref}")
        npc_id, dialogue_id = dialogue_ref.split(":", 1)
        return npc_id, dialogue_id
