from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.live import Live

from opengame.engine import GameEngine
from opengame.loader import load_game
from opengame.models import Choice, ContentError
from opengame.render import RichRenderer
from opengame.save import default_save_path, load_game_state, save_game_state
from opengame.validator import validate_game

app = typer.Typer(help="Play and validate modular YAML narrative games.")
console = Console()


def _load_valid_game(path: Path):
    game = load_game(path)
    issues = validate_game(game)
    if issues:
        messages = [_format_issue(issue.message, issue.scene_id) for issue in issues]
        raise ContentError("Validation failed:\n" + "\n".join(messages))
    return game


@app.command()
def play(
    path: Annotated[
        Path,
        typer.Argument(help="Path to a story pack directory."),
    ] = Path("content/sample_game"),
    resume: Annotated[
        bool,
        typer.Option("--resume", help="Resume from the save file before playing."),
    ] = False,
    save_file: Annotated[
        Path | None,
        typer.Option("--save-file", help="Path used by Ctrl+S and --resume."),
    ] = None,
) -> None:
    """Play a YAML story pack."""
    renderer = RichRenderer(console)
    try:
        game = _load_valid_game(path)
        save_path = save_file or default_save_path(game)
        state = load_game_state(game, save_path) if resume else None
        engine = GameEngine(game, state)
        selected_index = 0
        while True:
            choices = engine.visible_choices()

            if (engine.dialogue is None and engine.scene.ending) or not choices:
                _render_current(renderer, engine, choices, selected_index)
                raise typer.Exit(0)

            selected_index = min(selected_index, len(choices) - 1)
            _render_current_context(renderer, engine)
            translation: str | None = None
            with Live(
                renderer.choice_prompt(choices, selected_index),
                console=renderer.console,
                auto_refresh=False,
            ) as live:
                while True:
                    action = _read_choice_action()
                    if action == "up":
                        selected_index = (selected_index - 1) % len(choices)
                        translation = None
                        live.update(renderer.choice_prompt(choices, selected_index), refresh=True)
                    elif action == "down":
                        selected_index = (selected_index + 1) % len(choices)
                        translation = None
                        live.update(renderer.choice_prompt(choices, selected_index), refresh=True)
                    elif action == "select":
                        engine.choose(selected_index + 1)
                        selected_index = 0
                        break
                    elif action == "save":
                        save_game_state(engine.game, engine.state, save_path)
                        live.update(
                            renderer.choice_prompt(choices, selected_index, save_path, translation),
                            refresh=True,
                        )
                    elif action == "translate":
                        live.update(
                            renderer.choice_prompt(choices, selected_index, None, "⏳ Translating…"),
                            refresh=True,
                        )
                        from opengame.translate import translate_clipboard

                        translation = translate_clipboard()
                        live.update(
                            renderer.choice_prompt(choices, selected_index, None, translation),
                            refresh=True,
                        )
                    elif action == "quit":
                        console.print("[yellow]Goodbye.[/yellow]")
                        raise typer.Exit(0)
    except ContentError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(1) from exc


@app.command()
def validate(
    path: Annotated[
        Path,
        typer.Argument(help="Path to a story pack directory."),
    ] = Path("content/sample_game"),
) -> None:
    """Validate a story pack without playing it."""
    renderer = RichRenderer(console)
    try:
        game = load_game(path)
    except ContentError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(1) from exc

    issues = [_format_issue(issue.message, issue.scene_id) for issue in validate_game(game)]
    renderer.validation(issues)
    if issues:
        raise typer.Exit(1)


@app.command()
def inspect(
    path: Annotated[
        Path,
        typer.Argument(help="Path to a story pack directory."),
    ] = Path("content/sample_game"),
) -> None:
    """Show a summary of a story pack."""
    renderer = RichRenderer(console)
    try:
        renderer.inspect(load_game(path))
    except ContentError as exc:
        console.print(f"[bold red]{exc}[/bold red]")
        raise typer.Exit(1) from exc


def _format_issue(message: str, scene_id: str | None) -> str:
    if scene_id:
        return f"{scene_id}: {message}"
    return message


def _render_current(
    renderer: RichRenderer,
    engine: GameEngine,
    choices: list[Choice],
    selected_index: int | None,
) -> None:
    renderer.console.clear()
    dialogue = engine.dialogue
    if dialogue:
        renderer.dialogue(dialogue, choices, engine.state, engine.game, selected_index)
    else:
        step = engine.current_step
        renderer.scene(engine.scene, choices, engine.state, engine.game, selected_index, step)


def _render_current_context(renderer: RichRenderer, engine: GameEngine) -> None:
    renderer.console.clear()
    dialogue = engine.dialogue
    if dialogue:
        renderer.dialogue_context(dialogue, engine.state, engine.game)
    else:
        step = engine.current_step
        if step is not None:
            renderer.step_context(step, engine.scene.title, engine.state, engine.game)
        else:
            renderer.scene_context(engine.scene, engine.state, engine.game)


def _read_choice_action() -> str:
    if os.name == "nt":
        return _read_windows_choice_action()
    return _read_posix_choice_action()


def _read_windows_choice_action() -> str:
    import msvcrt

    key = msvcrt.getwch()
    if key in {"\x00", "\xe0"}:
        arrow = msvcrt.getwch()
        if arrow == "H":
            return "up"
        if arrow == "P":
            return "down"
    if key in {"\r", "\n"}:
        return "select"
    if key.lower() == "q":
        return "quit"
    if key == "\x13":
        return "save"
    if key == "\x14":
        return "translate"
    if key == "\x03":
        raise KeyboardInterrupt
    return "ignore"


def _read_posix_choice_action() -> str:
    import termios
    import tty

    stdin = sys.stdin.fileno()
    previous_settings = termios.tcgetattr(stdin)
    try:
        tty.setraw(stdin)
        key = sys.stdin.read(1)
        if key == "\x1b" and sys.stdin.read(1) == "[":
            arrow = sys.stdin.read(1)
            if arrow == "A":
                return "up"
            if arrow == "B":
                return "down"
        if key in {"\r", "\n"}:
            return "select"
        if key.lower() == "q":
            return "quit"
        if key == "\x13":
            return "save"
        if key == "\x14":
            return "translate"
        if key == "\x03":
            raise KeyboardInterrupt
        return "ignore"
    finally:
        termios.tcsetattr(stdin, termios.TCSADRAIN, previous_settings)
