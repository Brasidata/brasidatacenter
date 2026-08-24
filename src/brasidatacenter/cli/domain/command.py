"""Command contracts independent from presentation and plugin discovery."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Mapping, Sequence


class CommandArgumentError(ValueError):
    """Raised when no single command accepts the supplied arguments."""


@dataclass(frozen=True)
class CommandMetadata:
    """Identity and help information declared by a command plugin."""

    id: str
    logical_component: str
    description: str = ""
    usage: str = ""


@dataclass(frozen=True)
class CommandRequest:
    """Arguments normalized by the command router."""

    logical_component: str
    component_action: str
    command_args: tuple[str, ...] = ()


@dataclass(frozen=True)
class CommandTreeNode:
    """A node rendered in a command content tree."""

    label: str
    children: tuple["CommandTreeNode", ...] = ()


@dataclass(frozen=True)
class CommandTab:
    """A tab that may recursively contain nested tabs."""

    title: str
    children: tuple["CommandTab", ...] = ()
    tree: tuple[CommandTreeNode, ...] = ()


@dataclass(frozen=True)
class CommandResponse:
    """Presentation-neutral result returned by a command."""

    title: str
    description: str = ""
    content: Mapping[str, Any] = field(default_factory=dict)
    tabs: tuple[CommandTab, ...] = ()


class CommandPort(ABC):
    """Contract implemented by every auto-discovered command."""

    METADATA: ClassVar[CommandMetadata]

    def __init__(self, request: CommandRequest) -> None:
        self.request = request

    @staticmethod
    @abstractmethod
    def accepts(args: Sequence[str]) -> bool:
        """Return whether this command accepts the original CLI arguments."""

    @abstractmethod
    def check(self) -> bool:
        """Validate the normalized request before execution."""

    @abstractmethod
    def run(self) -> CommandResponse:
        """Execute the command and return a presentation-neutral response."""
