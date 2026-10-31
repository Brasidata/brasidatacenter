"""Looks a term up in what the ontologies call things: the kinds of the AECO taxonomy and the classes of IFC4.

A kind (a wall, a diaphragm wall, a floor trap) has a name in each language (``skos:prefLabel``), other names it is
known by (``skos:altLabel``) and, when the ontologies bind it to an IFC class (``domain/aeco/representation/bsi_ifc.ttl``),
the class it is in IFC. A person types the word they know, in any language, with or without accents or capitals: this finds
the kinds that word names and the IFC classes it leads to.
"""

from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from typing import Any

from rdflib import BNode, Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS

from brasidatacenter.resources import ontology_path
from brasidatacenter.tool.adapter import ontology_cache
from brasidatacenter.tool.adapter.class_definition import class_names

_KINDS: tuple[str, ...] = ("domain", "aeco", "taxonomy", "kind.ttl")
_BINDINGS: tuple[str, ...] = ("domain", "aeco", "representation", "bsi_ifc.ttl")
_AECO = Namespace("http://datacenter.app.br/ontology/domain/aeco/core/schema.ttl#")
_IFC4 = "https://standards.buildingsmart.org/IFC/DEV/IFC4/FINAL/OWL#"

#: How well a name must match to be shown, by what it is: the whole name, the start of it, whole words of it, the start of a word of it.
_EXACT, _START, _WORDS, _PART = 100, 80, 60, 40
#: A name the kind is known by besides its own counts less.
_ALTERNATIVE = 10


def _fold(text: str) -> str:
    """The text in lower case and without accents, so that ``Parede``, ``PAREDE`` and ``párêde`` are one word."""
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(character for character in decomposed if not unicodedata.combining(character))


def _compact(folded: str) -> str:
    return re.sub(r"[^0-9a-z]", "", folded)


def _local(node: Any) -> str:
    return str(node).rsplit("#", 1)[-1]


@lru_cache(maxsize=1)
def _kinds() -> list[dict[str, Any]]:
    """Each kind of the taxonomy: its identifier, its names by language, the others it is known by, its definitions."""
    graph: Graph = ontology_cache.parsed(ontology_path(*_KINDS))
    kinds: list[dict[str, Any]] = []
    for subject in graph.subjects(RDF.type, OWL.Class):
        if not isinstance(subject, URIRef):
            continue
        names: dict[str, str] = {}
        for label in graph.objects(subject, SKOS.prefLabel):
            names.setdefault(getattr(label, "language", None) or "", str(label))
        others = sorted({str(label) for label in graph.objects(subject, SKOS.altLabel)})
        definitions: dict[str, str] = {}
        for definition in graph.objects(subject, SKOS.definition):
            definitions.setdefault(getattr(definition, "language", None) or "", str(definition))
        if not names:
            continue
        kinds.append({"iri": str(subject), "identifier": _local(subject), "names": names, "others": others, "definitions": definitions})
    return kinds


@lru_cache(maxsize=1)
def _classes_of_kinds() -> dict[str, list[dict[str, str | None]]]:
    """The IFC classes each kind is bound to, by the IRI of the kind: the class, and the predefined type when the binding names one."""
    graph: Graph = ontology_cache.parsed(ontology_path(*_BINDINGS))
    bound: dict[str, list[dict[str, str | None]]] = {}
    for binding in graph.subjects(RDFS.subClassOf, _AECO.IfcElementBinding):
        classes: list[str] = []
        kinds: list[str] = []
        predefined: str | None = None
        for parent in graph.objects(binding, RDFS.subClassOf):
            if isinstance(parent, URIRef) and str(parent).startswith(_IFC4):
                classes.append(_local(parent))
            elif isinstance(parent, BNode):
                prop = graph.value(parent, OWL.onProperty)
                value = graph.value(parent, OWL.hasValue)
                if prop == _AECO.bindsIfcElementFor and value is not None:
                    kinds.append(str(value))
                elif prop is not None and _local(prop).startswith("predefinedType_") and value is not None:
                    predefined = _local(value)
        for kind in kinds:
            for name in classes:
                entry = {"class": name, "predefined": predefined}
                if entry not in bound.setdefault(kind, []):
                    bound[kind].append(entry)
    return bound


def _score(query: str, names: list[tuple[str, int]]) -> int:
    """How well the query names a kind: the best of its names, each with the weight it has. 0 when none does."""
    words = query.split()
    compact_query = _compact(query)
    best = 0
    for name, weight in names:
        folded = _fold(name)
        compact = _compact(folded)
        label_words = re.split(r"[^0-9a-z]+", folded)
        if not compact_query:
            continue
        if folded == query or compact == compact_query:
            score = _EXACT
        elif folded.startswith(query) or compact.startswith(compact_query):
            score = _START
        elif words and all(word in label_words for word in words):
            score = _WORDS
        elif words and all(any(label_word.startswith(word) for label_word in label_words) for word in words):
            score = _PART
        else:
            continue
        best = max(best, score - weight)
    return best


def search(term: str, limit: int = 8) -> dict[str, Any]:
    """
    What the term names: ``kinds``, the kinds of the taxonomy, best match first, each with its names by language, its
    definitions and the IFC classes it is bound to; and ``ifc_classes``, the classes of IFC4 whose name has the term in it.
    """
    query = _fold(term).strip()
    if not query:
        return {"kinds": [], "ifc_classes": []}

    bound = _classes_of_kinds()
    scored: list[tuple[int, int, dict[str, Any]]] = []
    for kind in _kinds():
        names = [(name, 0) for name in kind["names"].values()] + [(name, _ALTERNATIVE) for name in kind["others"]]
        score = _score(query, names)
        if score > 0:
            scored.append((score, len(min(kind["names"].values(), key=len)), kind))
    scored.sort(key=lambda item: (-item[0], item[1], item[2]["identifier"]))

    kinds = [
        {
            "identifier": kind["identifier"],
            "iri": kind["iri"],
            "names": kind["names"],
            "definitions": kind["definitions"],
            "ifc": bound.get(kind["iri"], []),
        }
        for _, _, kind in scored[:limit]
    ]
    compact_query = _compact(query)
    classes = sorted(
        (name for name in class_names() if compact_query and compact_query in _compact(_fold(name))),
        key=lambda name: (_compact(_fold(name)) != "ifc" + compact_query, len(name), name),
    )
    return {"kinds": kinds, "ifc_classes": classes[:limit]}
