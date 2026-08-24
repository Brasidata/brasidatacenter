"""Implementation of the ``brasidatacenter tool`` command."""

from __future__ import annotations

from collections.abc import Sequence
from importlib.resources.abc import Traversable
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from rdflib import BNode, Graph, URIRef
from rdflib.exceptions import ParserError
from rdflib.namespace import OWL, RDF, RDFS

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
                children=cls._class_property_nodes(file),
            )
            for file in files
        )

    @classmethod
    def _class_property_nodes(
        cls,
        resource: Traversable,
    ) -> tuple[CommandTreeNode, ...]:
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
        try:
            with resource.open("rb") as stream:
                graph.parse(file=stream, format=rdf_format)
        except (ParserError, SyntaxError):
            return ()

        classes = {
            subject
            for subject in graph.subjects(RDF.type, OWL.Class)
            if isinstance(subject, URIRef)
        }
        property_types = (OWL.ObjectProperty, OWL.DatatypeProperty)
        properties = {
            subject
            for property_type in property_types
            for subject in graph.subjects(RDF.type, property_type)
            if isinstance(subject, URIRef)
        }

        properties_by_domain: dict[URIRef, set[URIRef]] = {
            class_subject: set() for class_subject in classes
        }
        orphan_properties: set[URIRef] = set()
        for property_subject in properties:
            named_class_domains = {
                domain
                for domain in graph.objects(property_subject, RDFS.domain)
                if isinstance(domain, URIRef) and domain in classes
            }
            if named_class_domains:
                for domain in named_class_domains:
                    properties_by_domain[domain].add(property_subject)
            else:
                orphan_properties.add(property_subject)

        class_nodes = tuple(
            CommandTreeNode(
                label=cls._term_name(graph, class_subject),
                children=cls._property_nodes(
                    graph,
                    properties_by_domain[class_subject],
                ),
            )
            for class_subject in sorted(
                classes,
                key=lambda subject: cls._term_name(graph, subject).casefold(),
            )
        )
        if not orphan_properties:
            return class_nodes

        return (
            *class_nodes,
            CommandTreeNode(
                label="Orphan",
                children=cls._property_nodes(graph, orphan_properties),
            ),
        )

    @classmethod
    def _property_nodes(
        cls,
        graph: Graph,
        properties: set[URIRef],
    ) -> tuple[CommandTreeNode, ...]:
        return tuple(
            CommandTreeNode(
                label=cls._term_name(graph, property_subject),
                children=tuple(
                    CommandTreeNode(
                        label=(
                            "Anonymous range"
                            if isinstance(range_value, BNode)
                            else cls._term_name(graph, range_value)
                        )
                    )
                    for range_value in sorted(
                        set(graph.objects(property_subject, RDFS.range)),
                        key=str,
                    )
                ),
            )
            for property_subject in sorted(
                properties,
                key=lambda subject: cls._term_name(graph, subject).casefold(),
            )
        )

    @staticmethod
    def _term_name(graph: Graph, subject: URIRef) -> str:
        try:
            prefix, _, local_name = graph.namespace_manager.compute_qname(
                subject,
                generate=False,
            )
            return f"{prefix}:{local_name}" if prefix else local_name
        except (KeyError, ValueError):
            parsed = urlsplit(str(subject))
            fragment = unquote(parsed.fragment)
            if fragment:
                return fragment
            path_name = PurePosixPath(unquote(parsed.path)).name
            return path_name or str(subject)
