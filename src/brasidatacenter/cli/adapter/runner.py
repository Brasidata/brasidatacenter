"""Route raw arguments to exactly one auto-discovered command."""

from __future__ import annotations

from collections.abc import Sequence

from brasidatacenter.cli.adapter.loader import CommandLoader
from brasidatacenter.cli.domain.command import (
    CommandArgumentError,
    CommandPort,
    CommandRequest,
)


class CommandRunAdapter:
    """Create validated command instances from command-line arguments."""

    @classmethod
    def make(cls, args: Sequence[str]) -> CommandPort:
        original_args = tuple(args)
        logical_component = "cli"
        command_args = original_args
        command_classes = CommandLoader(logical_component).get_all()

        if original_args and not original_args[0].startswith("-"):
            scoped_component = original_args[0]
            scoped_commands = CommandLoader(scoped_component).get_all()
            if scoped_commands:
                logical_component = scoped_component
                command_args = original_args[1:]
                command_classes = scoped_commands

        candidates = [
            command_class
            for command_class in command_classes
            if command_class.accepts(original_args)
        ]

        if not candidates:
            raise CommandArgumentError(
                f"Invalid command arguments: {list(original_args)!r}"
            )
        if len(candidates) > 1:
            identifiers = ", ".join(
                command.METADATA.id for command in candidates
            )
            raise CommandArgumentError(
                "Multiple commands accept the supplied arguments: "
                f"{identifiers}."
            )

        command_class = candidates[0]
        request = CommandRequest(
            logical_component=logical_component,
            component_action=command_class.METADATA.id,
            command_args=command_args,
        )
        command = command_class(request)
        if not command.check():
            raise CommandArgumentError(
                f"Invalid command arguments: {list(original_args)!r}"
            )
        return command
