"""Unified Textual shell used by every interactive command."""

from __future__ import annotations

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane, Tree
from textual.widgets.tree import TreeNode

from brasidatacenter.cli.domain.command import (
    CommandResponse,
    CommandTab,
    CommandTreeNode,
)


class CommandBody(Vertical):
    """Render a command response inside the shared application shell."""

    def __init__(self, response: CommandResponse) -> None:
        super().__init__(id="command-body")
        self._response = response

    def compose(self) -> ComposeResult:
        if self._response.description:
            yield Static(self._response.description, id="command-description")

        if self._response.tabs:
            yield from self._compose_tabs(self._response.tabs, ())
        else:
            yield Static("No content available.", classes="empty-content")

    @classmethod
    def _compose_tabs(
        cls,
        tabs: tuple[CommandTab, ...],
        path: tuple[int, ...],
    ) -> ComposeResult:
        suffix = "-".join(str(index) for index in path) or "root"
        with TabbedContent(
            id=f"tabs-{suffix}",
            classes="command-tabs",
        ):
            for index, tab in enumerate(tabs):
                child_path = (*path, index)
                child_suffix = "-".join(str(value) for value in child_path)
                with TabPane(tab.title, id=f"tab-{child_suffix}"):
                    if tab.children:
                        yield from cls._compose_tabs(tab.children, child_path)
                    elif tab.tree:
                        yield cls._make_tree(tab.tree, child_suffix)
                    else:
                        yield Static(
                            "No files.",
                            classes="empty-directory",
                        )

    @classmethod
    def _make_tree(
        cls,
        nodes: tuple[CommandTreeNode, ...],
        suffix: str,
    ) -> Tree[None]:
        tree: Tree[None] = Tree(
            "Files",
            id=f"tree-{suffix}",
            classes="command-tree",
        )
        tree.show_root = False
        cls._add_tree_nodes(tree.root, nodes)
        tree.root.expand()
        return tree

    @classmethod
    def _add_tree_nodes(
        cls,
        parent: TreeNode[None],
        nodes: tuple[CommandTreeNode, ...],
    ) -> None:
        for node in nodes:
            if node.children:
                child = parent.add(node.label, expand=True)
                cls._add_tree_nodes(child, node.children)
            else:
                parent.add_leaf(node.label)


class CommandApplication(App[None]):
    """Fixed Header/Footer frame shared by all non-standalone commands."""

    TITLE = "BrasidataCenter"
    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]
    CSS = """
    Screen {
        background: #071a21;
        color: #e6edf3;
    }

    Header {
        dock: top;
        background: #10aec7;
        color: #00151b;
    }

    Footer {
        dock: bottom;
        background: #0b2b35;
        color: #e6edf3;
    }

    #command-body {
        height: 1fr;
        padding: 1 2;
    }

    #command-description {
        height: auto;
        margin-bottom: 1;
        color: #a9c6cf;
    }

    .command-tabs {
        height: 1fr;
    }

    .command-tree {
        height: 1fr;
        padding: 1 2;
        background: #071a21;
    }

    .empty-directory, .empty-content {
        padding: 2;
        color: #78909c;
        text-style: italic;
    }
    """

    def __init__(self, response: CommandResponse) -> None:
        super().__init__()
        self._response = response
        self.sub_title = response.title

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield CommandBody(self._response)
        yield Footer()
