import pytest

from brasidatacenter.__main__ import main
from brasidatacenter.cli.adapter.application import CommandApplication
from brasidatacenter.cli.adapter.runner import CommandRunAdapter


def test_tool_command_lists_tool_directories_as_tabs() -> None:
    response = CommandRunAdapter.make(["tool"]).run()

    assert [tab.title for tab in response.tabs] == ["infobim", "ontobdc"]
    children_by_package = {
        tab.title: {child.title for child in tab.children}
        for tab in response.tabs
    }
    assert {"abox", "entity", "tbox"} <= children_by_package["infobim"]
    assert {"abox", "entity", "tbox"} <= children_by_package["ontobdc"]

    ontobdc = next(tab for tab in response.tabs if tab.title == "ontobdc")
    tbox = next(tab for tab in ontobdc.children if tab.title == "tbox")
    ns_file = next(node for node in tbox.tree if node.label == "ns.ttl")
    class_nodes = {node.label: node for node in ns_file.children}

    assert "DataContainer" in class_nodes
    assert "ProjectManagementFramework" in class_nodes
    assert "belongsToDataContainer" not in class_nodes
    assert "dcterms:description" not in class_nodes
    assert "ns.ttl" not in class_nodes
    assert not any(name.startswith("_:") for name in class_nodes)

    data_container_properties = {
        node.label: node for node in class_nodes["DataContainer"].children
    }
    assert set(data_container_properties) == {"hasEntityDataset"}
    assert [
        node.label for node in data_container_properties["hasEntityDataset"].children
    ] == ["EntityDataset"]

    orphan_properties = {
        node.label: node for node in class_nodes["Orphan"].children
    }
    assert "dcterms:hasPart" in orphan_properties
    assert "usesProjectManagementFramework" in orphan_properties
    assert [
        node.label
        for node in orphan_properties["usesProjectManagementFramework"].children
    ] == ["ProjectManagementFramework"]


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
