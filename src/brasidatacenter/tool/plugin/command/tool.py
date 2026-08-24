"""Implementation of the ``brasidatacenter tool`` command."""

from __future__ import annotations

from collections.abc import Sequence
from importlib.resources.abc import Traversable
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from rdflib import Graph, URIRef

from brasidatacenter.cli.domain.command import (
    CommandMetadata,
    CommandPort,
    CommandResponse,
    CommandTab,
    CommandTreeNode,
)
from brasidatacenter.resources import ontology_path


class ToolCommand(CommandPort):
    """List the tool packages bundled in BrasidataCenter."""

    METADATA = CommandMetadata(
        id="tool",
        logical_component="tool",
        description="Browse tool packages distributed by BrasidataCenter.",
        usage="brasidatacenter tool",
    )

    @staticmethod
    def accepts(args: Sequence[str]) -> bool:
        return tuple(args) == ("tool",)

    def check(self) -> bool:
        return self.request.command_args == ()

    def run(self) -> CommandResponse:
        tabs = self._directory_tabs(ontology_path("tool"))
        return CommandResponse(
            title="Tool Packages",
            description="Directories available under brasidatacenter/ontology/tool.",
            tabs=tabs,
        )

    @classmethod
    def _directory_tabs(cls, directory: Traversable) -> tuple[CommandTab, ...]:
        if not directory.is_dir():
            return ()

        directories = sorted(
            (child for child in directory.iterdir() if child.is_dir()),
            key=lambda child: child.name.casefold(),
        )
        return tuple(
            CommandTab(
                title=child.name,
                children=cls._directory_tabs(child),
                tree=cls._file_tree(child),
            )
            for child in directories
        )

    @classmethod
    def _file_tree(cls, directory: Traversable) -> tuple[CommandTreeNode, ...]:
        files = sorted(
            (
                child
                for child in directory.iterdir()
                if not child.is_dir() and not child.name.startswith(".")
            ),
            key=lambda child: child.name.casefold(),
        )
        return tuple(
            CommandTreeNode(
                label=file.name,
                children=cls._subject_nodes(file),
            )
            for file in files
        )

    @classmethod
    def _subject_nodes(cls, resource: Traversable) -> tuple[CommandTreeNode, ...]:
        rdf_format = {
            ".json": "json-ld",
            ".jsonld": "json-ld",
            ".n3": "n3",
            ".nq": "nquads",
            ".nt": "nt",
            ".owl": "xml",
            ".rdf": "xml",
            ".trig": "trig",
            ".ttl": "turtle",
        }.get(PurePosixPath(resource.name).suffix.casefold())
        if rdf_format is None:
            return ()

        graph = Graph()
        with resource.open("rb") as stream:
            graph.parse(file=stream, format=rdf_format)

        names = {
            cls._subject_name(graph, subject)
            for subject in graph.subjects()
            if isinstance(subject, URIRef)
        }
        return tuple(
            CommandTreeNode(label=name)
            for name in sorted(names, key=str.casefold)
        )

    @staticmethod
    def _subject_name(graph: Graph, subject: URIRef) -> str:
        try:
            prefix, _, local_name = graph.namespace_manager.compute_qname(
                subject,
                generate=False,
            )
            return f"{prefix}:{local_name}" if prefix else local_name
        except KeyError:
            parsed = urlsplit(str(subject))
            fragment = unquote(parsed.fragment)
            if fragment:
                return fragment
            path_name = PurePosixPath(unquote(parsed.path)).name
            return path_name or str(subject)
