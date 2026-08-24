from __future__ import annotations

import importlib
from pathlib import Path

from brasidatacenter.cli.adapter.loader import CommandLoader
from brasidatacenter.tool.plugin.command.tool import ToolCommand


def test_discovers_tool_command_by_convention() -> None:
    assert "tool" in CommandLoader.logical_components()
    assert CommandLoader("tool").get_all() == [ToolCommand]
    assert CommandLoader("tool").get("tool") is ToolCommand


def test_discovers_commands_in_an_independent_root_package(
    tmp_path: Path,
    monkeypatch,
) -> None:
    files = {
        "fake_commands/__init__.py": "",
        "fake_commands/demo/__init__.py": "",
        "fake_commands/demo/plugin/__init__.py": "",
        "fake_commands/demo/plugin/command/__init__.py": "",
        "fake_commands/demo/plugin/command/sample.py": """
from brasidatacenter.cli.domain.command import (
    CommandMetadata, CommandPort, CommandResponse,
)

class SampleCommand(CommandPort):
    METADATA = CommandMetadata(id="sample", logical_component="demo")

    @staticmethod
    def accepts(args):
        return tuple(args) == ("demo",)

    def check(self):
        return True

    def run(self):
        return CommandResponse(title="sample")
""",
    }
    for relative_path, content in files.items():
        target = tmp_path / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()

    commands = CommandLoader("demo", root_package="fake_commands").get_all()

    assert [command.METADATA.id for command in commands] == ["sample"]
