import pytest

from brasidatacenter.__main__ import main
from brasidatacenter.cli.adapter.application import CommandApplication
from brasidatacenter.cli.adapter.runner import CommandRunAdapter


def test_tool_command_lists_tool_directories_as_tabs() -> None:
    response = CommandRunAdapter.make(["tool"]).run()

    assert [tab.title for tab in response.tabs] == ["infobim", "ontobdc"]
    assert {
        tab.title: [child.title for child in tab.children]
        for tab in response.tabs
    } == {
        "infobim": ["abox", "tbox"],
        "ontobdc": ["abox", "tbox"],
    }


def test_tool_command_runs_through_the_shared_application(monkeypatch) -> None:
    responses = []
    monkeypatch.setattr(
        CommandApplication,
        "run",
        lambda application: responses.append(application._response),
    )

    exit_code = main(["tool"])

    assert exit_code == 0
    assert len(responses) == 1
    assert responses[0].title == "Tool Packages"


@pytest.mark.parametrize("arguments", [["--help"], ["--version"]])
def test_help_and_version_remain_standalone(arguments, monkeypatch) -> None:
    def reject_application_run(_application) -> None:
        raise AssertionError("standalone output started the Textual application")

    monkeypatch.setattr(CommandApplication, "run", reject_application_run)

    assert main(arguments) == 0
