from __future__ import annotations

from pathlib import Path

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from opengame.models import Choice, DialogueNode, GameData, GameState, Scene, Step


class RichRenderer:
    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def scene(
        self,
        scene: Scene,
        choices: list[Choice],
        state: GameState,
        game: GameData,
        selected_index: int | None = None,
        current_step: Step | None = None,
    ) -> None:
        if current_step is not None:
            self.step_context(current_step, scene.title, state, game)
        else:
            self.scene_context(scene, state, game)

        if scene.ending:
            self.console.print("[bold green]The End[/bold green]")
            return

        self.choices(choices, selected_index)

    def dialogue(
        self,
        dialogue: DialogueNode,
        choices: list[Choice],
        state: GameState,
        game: GameData,
        selected_index: int | None = None,
    ) -> None:
        self.dialogue_context(dialogue, state, game)
        self.choices(choices, selected_index)

    def scene_context(self, scene: Scene, state: GameState, game: GameData) -> None:
        self.console.print()
        self.console.print(Panel(scene.text.strip(), title=scene.title, border_style="cyan"))
        self.status(state, game)

    def step_context(self, step: Step, scene_title: str, state: GameState, game: GameData) -> None:
        self.console.print()
        if step.author:
            body = f"[bold magenta]{step.author}[/bold magenta]\n\n{step.text.strip()}"
        else:
            body = step.text.strip()
        self.console.print(Panel(body, title=scene_title, border_style="cyan"))
        self.status(state, game)

    def dialogue_context(self, dialogue: DialogueNode, state: GameState, game: GameData) -> None:
        self.console.print()
        self.console.print(Panel(dialogue.text.strip(), title=dialogue.title, border_style="magenta"))
        self.status(state, game)

    def choices(self, choices: list[Choice], selected_index: int | None = None) -> None:
        self.console.print(self.choice_list(choices, selected_index))

    def choice_prompt(
        self,
        choices: list[Choice],
        selected_index: int | None = None,
        saved_path: Path | None = None,
        translation: str | None = None,
    ) -> Group:
        help_text = "Up/Down to choose · Enter to select · Ctrl+S save · Ctrl+T translate · q quit"
        if saved_path is not None:
            help_text = f"Saved to {saved_path}. " + help_text
        parts: list = [self.choice_list(choices, selected_index), Text(help_text, style="dim")]
        if translation is not None:
            panel = Panel(
                translation,
                title="[bold yellow]Translation[/bold yellow]",
                border_style="yellow",
                padding=(0, 1),
            )
            parts.append(Align(panel, align="right"))
        return Group(*parts)

    def choice_list(self, choices: list[Choice], selected_index: int | None = None) -> Group | Text:
        if not choices:
            return Text("No available choices. The story cannot continue from here.", style="yellow")

        lines: list[Text] = []
        for index, choice in enumerate(choices):
            display_number = index + 1
            line = Text()
            if index == selected_index:
                line.append(f"> {display_number}.", style="bold cyan")
                line.append(" ")
                line.append(choice.text, style="bold")
            else:
                line.append(f"  {display_number}.", style="cyan")
                line.append(f" {choice.text}")
            lines.append(line)

        return Group(*lines)

    def status(self, state: GameState, game: GameData) -> None:
        if state.inventory:
            inventory = ", ".join(game.items[item_id].name for item_id in sorted(state.inventory) if item_id in game.items)
            self.console.print(f"[bold]Inventory:[/bold] {inventory}")

        visible_quests = [
            (quest_id, status)
            for quest_id, status in sorted(state.quests.items())
            if status in {"active", "completed"}
        ]
        if visible_quests:
            quests = ", ".join(f"{game.quests[quest_id].title} ({status})" for quest_id, status in visible_quests)
            self.console.print(f"[bold]Quests:[/bold] {quests}")

        visible_relationships = [
            (npc_id, value)
            for npc_id, value in sorted(state.relationships.items())
            if value != 0 and npc_id in game.npcs
        ]
        if visible_relationships:
            relationships = ", ".join(f"{game.npcs[npc_id].name} ({value:+d})" for npc_id, value in visible_relationships)
            self.console.print(f"[bold]Relationships:[/bold] {relationships}")

    def validation(self, issues: list[str]) -> None:
        if not issues:
            self.console.print("[bold green]Story pack is valid.[/bold green]")
            return

        self.console.print("[bold red]Story pack has validation issues:[/bold red]")
        for issue in issues:
            self.console.print(f" - {issue}")

    def inspect(self, game: GameData) -> None:
        table = Table(title=game.title)
        table.add_column("Field", style="bold cyan")
        table.add_column("Value")
        table.add_row("ID", game.id)
        table.add_row("Version", str(game.version))
        table.add_row("Author", game.author or "Unknown")
        table.add_row("Start Scene", game.start_scene)
        table.add_row("Scenes", str(len(game.scenes)))
        table.add_row("Items", str(len(game.items)))
        table.add_row("Quests", str(len(game.quests)))
        table.add_row("NPCs", str(len(game.npcs)))
        table.add_row("Flags", str(len(game.flags)))
        table.add_row("Counters", str(len(game.counters)))
        self.console.print(table)
