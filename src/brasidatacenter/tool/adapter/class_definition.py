"""What the IFC4 ontology says about an IFC class: where it stands in the hierarchy, its attributes and its types.

The ontology (``third_party/ifc4_owl.ttl``) is large, and parsing it takes far longer than a command should. It is read as
text: each class is a block of the file, so the one asked about is found by its name, parsed alone, and the rest of
the file is only indexed (who is the parent of whom, which values an enumeration has).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from importlib.resources import files
from typing import Any

from rdflib import BNode, Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

#: The namespace the ontologies of this package, and the models, name the classes of IFC4 by.
IFC4_NAMESPACE = "https://standards.buildingsmart.org/IFC/DEV/IFC4/FINAL/OWL#"
#: The one the file is written in.
_FILE_NAMESPACE = "http://standards.buildingsmart.org/IFC/DEV/IFC4/FINAL/OWL#"
_IFC = Namespace(_FILE_NAMESPACE)

_SUBJECT = re.compile(r"^ifc:(\w+)\s", re.MULTILINE)
_SUPERS = re.compile(r"rdfs:subClassOf\s+((?:ifc:\w+\s*,?\s*)+);")
_MEMBER = re.compile(r"\sa\s+ifc:(\w+Enum)\b")
_LABEL = re.compile(r'rdfs:label\s+"([^"]+)"')


@dataclass
class _Index:
    prefixes: str
    blocks: dict[str, str] = field(default_factory=dict)
    parent: dict[str, str] = field(default_factory=dict)
    children: dict[str, list[str]] = field(default_factory=dict)
    members: dict[str, list[str]] = field(default_factory=dict)


_INDEX: _Index | None = None


def _index() -> _Index:
    """The file, split into its blocks and indexed once per process."""
    global _INDEX
    if _INDEX is not None:
        return _INDEX

    text = files("brasidatacenter").joinpath("third_party/ifc4_owl.ttl").read_text(encoding="utf-8")
    index = _Index(prefixes="\n".join(line for line in text.split("\n\n", 1)[0].splitlines() if line.startswith("@prefix")))
    for block in text.split("\n\n"):
        subject = _SUBJECT.match(block)
        if subject is None:
            continue
        name = subject.group(1)
        index.blocks[name] = block
        enumeration = _MEMBER.search(block.split(";", 1)[0]) if name.isupper() else None
        if enumeration is not None:
            label = _LABEL.search(block)
            index.members.setdefault(enumeration.group(1), []).append(label.group(1) if label else name)
        elif "owl:Class" in block.split(";", 1)[0]:
            parent = _parent_of(block)
            if parent is not None:
                index.parent[name] = parent
                index.children.setdefault(parent, []).append(name)
    _INDEX = index
    return index


def _parent_of(block: str) -> str | None:
    """The class a class is a kind of: the first it names that is not a select (a union of types a class may also belong to)."""
    for line in _SUPERS.finditer(block):
        for name in re.findall(r"ifc:(\w+)", line.group(1)):
            if not name.endswith("Select"):
                return name
    return None


def _local(node: Any) -> str:
    return str(node).rsplit("#", 1)[-1]


def class_name(iri: str) -> str | None:
    """The name of the IFC4 class the IRI is of, whichever way its namespace is written; none for any other IRI."""
    for namespace in (IFC4_NAMESPACE, _FILE_NAMESPACE):
        if iri.startswith(namespace) and iri[len(namespace):].isidentifier():
            return iri[len(namespace):]
    return None


def class_definition(iri: str) -> dict[str, Any] | None:
    """
    The definition of an IFC4 class: ``entity_iri``, ``name``, its ``superclasses`` (nearest first), its direct
    ``subclasses``, its own ``attributes`` (name, type, whether it takes many values) and, when it has one, the values
    of its ``predefined_types``. None when the IRI is not of a class of the ontology.
    """
    name = class_name(iri)
    index = _index()
    block = index.blocks.get(name) if name else None
    if name is None or block is None or "owl:Class" not in block.split(";", 1)[0]:
        return None

    graph = Graph()
    graph.parse(data=f"{index.prefixes}\n{block}", format="turtle")
    subject = URIRef(_FILE_NAMESPACE + name)
    attributes: list[dict[str, Any]] = []
    predefined: list[str] = []
    for restriction in graph.objects(subject, RDFS.subClassOf):
        if not isinstance(restriction, BNode):
            continue
        prop = graph.value(restriction, OWL.onProperty)
        kind = graph.value(restriction, OWL.allValuesFrom) or graph.value(restriction, OWL.onClass)
        if prop is None or kind is None:
            continue
        attribute = _local(prop).split("_", 1)[0]
        # An attribute says its range twice (every value is of it, at most one is); the one that bounds it is what it takes.
        many = graph.value(restriction, OWL.allValuesFrom) is not None and not any(
            graph.value(other, OWL.onProperty) == prop and graph.value(other, OWL.maxQualifiedCardinality) is not None
            for other in graph.objects(subject, RDFS.subClassOf)
            if isinstance(other, BNode)
        )
        if any(item["name"] == attribute for item in attributes):
            continue
        attributes.append({"name": attribute, "type": _local(kind), "many": many})
        if attribute == "predefinedType":
            predefined = list(index.members.get(_local(kind), []))

    lineage: list[str] = []
    parent = index.parent.get(name)
    while parent is not None and parent not in lineage:
        lineage.append(parent)
        parent = index.parent.get(parent)

    return {
        "entity_iri": IFC4_NAMESPACE + name,
        "name": name,
        "superclasses": lineage,
        "subclasses": sorted(index.children.get(name, [])),
        "attributes": attributes,
        "predefined_types": sorted(predefined),
    }
