from __future__ import annotations

import asyncio

from textual.widgets import Footer, Header, TabbedContent, TabPane, Tree

from brasidatacenter.cli.adapter.application import CommandApplication
from brasidatacenter.cli.domain.command import (
    CommandResponse,
    CommandTab,
    CommandTreeNode,
)


def test_application_has_one_fixed_header_and_footer_and_nested_tabs() -> None:
    response = CommandResponse(
        title="Test Command",
        tabs=(
            CommandTab(
                title="primary",
                children=(
                    CommandTab(
                        title="nested",
                        tree=(
                            CommandTreeNode(
                                label="schema.ttl",
                                children=(CommandTreeNode(label="Entity"),),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    application = CommandApplication(response)

    async def inspect_application() -> None:
        async with application.run_test():
            assert len(application.query(Header)) == 1
            assert len(application.query(Footer)) == 1
            assert str(application.query_one(Header).styles.dock) == "top"
            assert str(application.query_one(Footer).styles.dock) == "bottom"
            assert len(application.query(TabbedContent)) == 2
            assert [pane.id for pane in application.query(TabPane)] == [
                "tab-0",
                "tab-0-0",
            ]
            trees = list(application.query(Tree))
            assert len(trees) == 1
            assert str(trees[0].root.children[0].label) == "schema.ttl"
            assert str(trees[0].root.children[0].children[0].label) == "Entity"

    asyncio.run(inspect_application())
