"""Autonomous command-line entry point for BrasidataCenter."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from brasidatacenter import __version__
from brasidatacenter.cli.adapter.application import CommandApplication
from brasidatacenter.cli.adapter.loader import CommandDiscoveryError, CommandLoader
from brasidatacenter.cli.adapter.runner import CommandRunAdapter
from brasidatacenter.cli.domain.command import CommandArgumentError

_REPO_URL = "https://github.com/Brasidata/brasidatacenter"
_TAGLINE = "BrasidataCenter ontology distribution package"


def _build_options_table() -> Table:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="cyan", no_wrap=True)
    table.add_column(style="yellow bold", no_wrap=True)
    table.add_column(style="white")
    table.add_row("-h", "--help", "Show this message and exit.")
    table.add_row("", "--version", "Show the version and exit.")
    return table


def _build_commands_table() -> Table:
    table = Table.grid(padding=(0, 2))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column(style="white")

    for component in CommandLoader.logical_components():
        for command_class in CommandLoader(component).get_all():
            table.add_row(
                command_class.METADATA.usage,
                command_class.METADATA.description,
            )
    return table


def _render_help(console: Console) -> None:
    console.print()
    console.print(
        Align.center(
            Text.assemble(
                ("BrasidataCenter CLI ", "bold"),
                (f"v{__version__} ", "bold magenta"),
                ("\U0001F5FA", ""),
            )
        )
    )
    console.print(Align.center(Text(_TAGLINE, style="dim")))
    console.print()
    console.print(
        Text.assemble(
            ("Usage: ", "bold"),
            ("brasidatacenter ", "bold cyan"),
            ("[OPTIONS] ", "yellow"),
            ("<COMMAND>", "bold yellow"),
        )
    )
    console.print()
    console.print(
        Panel(
            _build_options_table(),
            title="Options",
            title_align="left",
            border_style="grey50",
            padding=(1, 2),
        )
    )
    console.print(
        Panel(
            _build_commands_table(),
            title="Commands",
            title_align="left",
            border_style="grey50",
            padding=(1, 2),
        )
    )
    console.print(Align.right(Text(f"♥ {_REPO_URL}", style="magenta dim")))
    console.print()


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    console = Console()

    if not arguments or arguments[0] in ("-h", "--help"):
        _render_help(console)
        return 0

    if arguments == ["--version"]:
        console.print(f"brasidatacenter {__version__}")
        return 0

    try:
        command = CommandRunAdapter.make(arguments)
        response = command.run()
    except (CommandArgumentError, CommandDiscoveryError) as error:
        console.print(f"[bold red]brasidatacenter:[/bold red] {error}")
        return 1

    CommandApplication(response).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
