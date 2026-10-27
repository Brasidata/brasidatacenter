"""The ontologies this package ships, parsed once per process.

The ontologies do not change while a process runs, and parsing them is what
costs most when entities are described: the same files used to be parsed again
by every call, hundreds of times for one command. A graph or a text from here is
shared, so it must only be read; ``copy`` gives a graph that can be changed.
"""

from __future__ import annotations

from typing import Any

from rdflib import Graph
from rdflib.util import guess_format

_GRAPHS: dict[str, Graph] = {}
_TEXTS: dict[str, str] = {}


def parsed(ontology_file: Any) -> Graph:
    """The graph of the file, shared: it is not to be changed."""
    key = str(ontology_file)
    graph = _GRAPHS.get(key)
    if graph is None:
        graph = Graph()
        graph.parse(key, format=guess_format(key))
        _GRAPHS[key] = graph
    return graph


def text(ontology_file: Any) -> str:
    """The text of the file, read once. Looking for a word in it is much faster than parsing it."""
    key = str(ontology_file)
    content = _TEXTS.get(key)
    if content is None:
        content = ontology_file.read_text(encoding="utf-8")
        _TEXTS[key] = content
    return content


def copy(ontology_file: Any) -> Graph:
    """A graph with what the file says, that the caller may change."""
    shared = parsed(ontology_file)
    graph = Graph()
    for prefix, namespace in shared.namespaces():
        graph.bind(prefix, namespace, override=False)
    graph += shared
    return graph
