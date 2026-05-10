from rich.console import Console

from opengame.models import Choice
from opengame.render import RichRenderer


def test_selected_choice_is_bold_and_marked() -> None:
    console = Console(record=True, force_terminal=True, width=80)
    renderer = RichRenderer(console)

    renderer.choices(
        [
            Choice("Take the lantern", target="lantern"),
            Choice("Open the gate", target="gate"),
        ],
        selected_index=1,
    )

    plain_output = console.export_text(clear=False)
    styled_output = console.export_text(styles=True)

    assert "> 2." in plain_output
    assert "\x1b[1mOpen the gate\x1b[0m" in styled_output
