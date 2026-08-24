import pytest

from brasidatacenter.cli.adapter.runner import CommandRunAdapter
from brasidatacenter.cli.domain.command import CommandArgumentError
from brasidatacenter.tool.plugin.command.tool import ToolCommand


def test_routes_component_and_removes_it_from_command_arguments() -> None:
    command = CommandRunAdapter.make(["tool"])

    assert isinstance(command, ToolCommand)
    assert command.request.logical_component == "tool"
    assert command.request.component_action == "tool"
    assert command.request.command_args == ()


@pytest.mark.parametrize("arguments", [["unknown"], ["tool", "extra"]])
def test_rejects_arguments_not_accepted_by_exactly_one_command(arguments) -> None:
    with pytest.raises(CommandArgumentError):
        CommandRunAdapter.make(arguments)
