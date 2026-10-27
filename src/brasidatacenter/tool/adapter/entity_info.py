"""Describes entities using the ontologies this package ships."""

from __future__ import annotations

import copy
from typing import Any

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, XSD, Namespace

from brasidatacenter.resources import iter_ontology_files, ontology_path_for_iri
from brasidatacenter.tool.adapter import ontology_cache

_FACADE = Namespace("http://datacenter.app.br/ontology/tool/ontobdc/facade/ns.ttl#")
_SCHEMA = Namespace("http://schema.org/")
_CSVW = Namespace("http://www.w3.org/ns/csvw#")
_DCTERMS = Namespace("http://purl.org/dc/terms/")
_SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
_SH = Namespace("http://www.w3.org/ns/shacl#")
_OBDC = Namespace("http://datacenter.app.br/ontology/tool/ontobdc/core/ns.ttl#")
_DATA_ENTITY = URIRef("http://datacenter.app.br/ontology/tool/ontobdc/core/ns.ttl#DataEntity")


def entity_info(entity_id: str | None = None) -> dict[str, Any] | list[dict[str, Any]] | None:
    """
    With no argument, list the entities this package declares: one item per
    direct subclass of ``core/ns.ttl:DataEntity``, as
    ``{"entity_iri": ..., "facade": ...}``, where ``facade`` is what
    ``entity_info(entity_iri)`` returns. A subclass of a subclass of
    ``DataEntity`` is not listed, nor is a subclass of any other class (for
    example ``SurfaceableEntity``).

    With ``entity_id``, return the facade this package publishes for that
    entity IRI: its identifier, display name, and declared fields. Scans
    every ontology this package ships for a
    ``facade:DataEntityFacade`` whose ``facade:isFacadeOf`` is ``entity_id``.
    Returns ``None`` when no ontology publishes one.

    Raises:
        ValueError: a matching facade is missing something a field needs.
    """
    if entity_id is None:
        return [
            {"entity_iri": entity_iri, "facade": entity_info(entity_iri)}
            for entity_iri in _data_entity_types()
        ]

    # What the ontologies say does not change while the process runs: it is worked out once for each entity.
    if entity_id not in _FACADES:
        _FACADES[entity_id] = _facade_published_for(entity_id)
    return copy.deepcopy(_FACADES[entity_id])


_FACADES: dict[str, dict[str, Any] | None] = {}


def _facade_published_for(entity_id: str) -> dict[str, Any] | None:
    for ontology_file in iter_ontology_files():
        # A facade is in a file that names the entity: the others are not even parsed.
        if _local_name(URIRef(entity_id)) not in ontology_cache.text(ontology_file):
            continue
        shared = ontology_cache.parsed(ontology_file)
        subject = _facade_of(shared, entity_id)
        if subject is not None:
            # Reading the facade brings other ontologies in: it works on a copy, the shared graph stays as it was.
            return _read(ontology_cache.copy(ontology_file), subject, entity_id)

    return None


def _tree_children(graph: Graph, subject: URIRef) -> list[dict[str, Any]]:
    """
    What a facade says about the children of its entity in a tree view
    (``facade:hasTreeViewChild``): for each, the facade of the children, the
    class of entity that facade is of, and the SHACL property path that
    leads from an instance of the parent to its children. Empty for a facade
    that declares none: its entity is a leaf of the tree.

    Raises:
        ValueError: a child declares no facade or no path, or its path uses a
            SHACL construct this adapter does not read.
    """
    children: list[dict[str, Any]] = []
    for child in graph.objects(subject, _FACADE.hasTreeViewChild):
        facade = graph.value(child, _FACADE.childFacade)
        path = graph.value(child, _FACADE.childPath)
        if not isinstance(facade, URIRef) or path is None:
            raise ValueError(f"The tree-view child of {subject} declares no child facade or no child path.")

        entity = graph.value(facade, _FACADE.isFacadeOf)
        if entity is None:
            entity = _find(facade, _FACADE.isFacadeOf)
        children.append(
            {
                "facade_iri": str(facade),
                "entity_iri": str(entity) if entity is not None else None,
                "path": _property_path(graph, path),
            }
        )

    return sorted(children, key=lambda declared: (declared["facade_iri"], str(declared["path"])))


def _property_path(graph: Graph, node: Any) -> dict[str, Any]:
    """
    A SHACL property path as plain data: ``{"predicate": iri}``, or one of
    ``inverse``, ``sequence``, ``alternative``, ``zeroOrMore``, ``oneOrMore``
    and ``zeroOrOne`` holding the path or paths they apply to.
    """
    if isinstance(node, URIRef):
        return {"predicate": str(node)}

    if not isinstance(node, BNode):
        raise ValueError(f"A property path is an IRI or a blank node, not {node!r}.")

    for key, predicate in (
        ("inverse", _SH.inversePath),
        ("zeroOrMore", _SH.zeroOrMorePath),
        ("oneOrMore", _SH.oneOrMorePath),
        ("zeroOrOne", _SH.zeroOrOnePath),
    ):
        inner = graph.value(node, predicate)
        if inner is not None:
            return {key: _property_path(graph, inner)}

    alternatives = graph.value(node, _SH.alternativePath)
    if alternatives is not None:
        return {"alternative": [_property_path(graph, step) for step in _list_items(graph, alternatives)]}

    if graph.value(node, RDF.first) is not None:
        return {"sequence": [_property_path(graph, step) for step in _list_items(graph, node)]}

    raise ValueError(f"The property path {node} uses a SHACL construct this adapter does not read.")


def _list_items(graph: Graph, head: Any) -> list[Any]:
    items: list[Any] = []
    while head is not None and head != RDF.nil:
        items.append(graph.value(head, RDF.first))
        head = graph.value(head, RDF.rest)

    return items


def _data_entity_types() -> list[str]:
    """
    The direct subclasses of ``DataEntity``.

    Reading a file's text and looking for a word is about 400 times faster
    than parsing it, so a file is parsed only when its text contains both
    ``subClassOf`` and ``DataEntity``. The search needs no external program,
    so it works the same inside an installed wheel.
    """
    global _DATA_ENTITY_TYPES
    if _DATA_ENTITY_TYPES is None:
        known: set[str] = set()
        for ontology_file in iter_ontology_files():
            text = ontology_cache.text(ontology_file)
            if "subClassOf" in text and _local_name(_DATA_ENTITY) in text:
                graph = ontology_cache.parsed(ontology_file)
                known.update(str(type_) for type_ in graph.subjects(RDFS.subClassOf, _DATA_ENTITY) if isinstance(type_, URIRef))
        _DATA_ENTITY_TYPES = sorted(known)

    return list(_DATA_ENTITY_TYPES)


_DATA_ENTITY_TYPES: list[str] | None = None


def _local_name(iri: URIRef) -> str:
    return str(iri).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _facade_of(graph: Graph, entity_iri: str) -> URIRef | None:
    for subject in graph.subjects(RDF.type, _FACADE.DataEntityFacade):
        if (subject, _FACADE.isFacadeOf, URIRef(entity_iri)) in graph:
            return subject if isinstance(subject, URIRef) else None

    return None


def _bring_in_fields(graph: Graph, subject: URIRef) -> None:
    """
    A field the facade lists but the file of the facade does not describe is described in the ontology
    that names it: a field is an IRI, and an ontology is published at the IRI that names its file. Its
    description is read from there, so a field can be shared by the facades of many ontologies.
    """
    for field_subject in list(graph.objects(subject, _FACADE.hasFacadeField)):
        if not isinstance(field_subject, URIRef) or graph.value(field_subject, _SCHEMA.identifier) is not None:
            continue

        ontology_file = ontology_path_for_iri(str(field_subject).split("#", 1)[0])
        graph += ontology_cache.parsed(ontology_file)


def _read(graph: Graph, subject: URIRef, entity_iri: str) -> dict[str, Any]:
    _bring_in_fields(graph, subject)
    fields = [
        _read_field(graph, field_subject)
        for field_subject in graph.objects(subject, _FACADE.hasFacadeField)
        if isinstance(field_subject, URIRef)
    ]
    return {
        "identifier": _required_text(graph, subject, _SCHEMA.identifier),
        "name": _label(graph, subject),
        "labels": _labels(graph, subject),
        "deletable": _deletable(graph, subject),
        "creatable": _creatable(graph, subject),
        "commentable": _commentable(graph, subject),
        "entity_iri": entity_iri,
        "tree_children": _tree_children(graph, subject),
        "fields": sorted(fields, key=lambda declared: declared["order"]),
    }


def _read_field(graph: Graph, subject: URIRef) -> dict[str, Any]:
    return {
        "identifier": _required_text(graph, subject, _SCHEMA.identifier),
        "datatype": _required_text(graph, subject, _FACADE.fieldDatatype),
        "order": int(_required_text(graph, subject, _FACADE.fieldOrder)),
        "required": _flag(graph, subject, _FACADE.isRequired),
        "multivalued": _flag(graph, subject, _FACADE.isMultivalued),
        "editable": _editable(graph, subject),
        "default": _default(graph, subject),
        **_options(graph, subject),
        "resource_facade": _resource_facade(graph, subject),
        "alternative_visualization": _alternative_visualization(graph, subject),
        "maps_to_resource": _required_text(graph, subject, _FACADE.mapsToResource),
        "labels": _labels(graph, subject),
        "formats": _formats(graph, subject),
    }


def _formats(graph: Graph, subject: URIRef) -> dict[str, str]:
    """The masks the field is shown with (``csvw:format``), by lower-case language tag."""
    return {
        str(mask.language).lower(): str(mask)
        for mask in graph.objects(subject, _CSVW["format"])
        if isinstance(mask, Literal) and mask.language
    }


def _labels(graph: Graph, subject: URIRef) -> dict[str, str]:
    """The names the facade or one of its fields has, by lower-case language tag."""
    return {
        str(label.language).lower(): str(label)
        for label in graph.objects(subject, _SCHEMA.name)
        if isinstance(label, Literal) and label.language
    }


def _required_text(graph: Graph, subject: URIRef, predicate: URIRef) -> str:
    value = graph.value(subject, predicate)
    if value is None or not str(value).strip():
        raise ValueError(f"The facade declares no {predicate} for {subject}.")

    return str(value).strip()


def _flag(graph: Graph, subject: URIRef, predicate: URIRef) -> bool:
    value = graph.value(subject, predicate)
    if not isinstance(value, Literal) or value.datatype != XSD.boolean:
        raise ValueError(f"The facade declares no boolean {predicate} for {subject}.")

    return bool(value.toPython())


def _resource_facade(graph: Graph, subject: URIRef) -> dict[str, Any] | None:
    """
    The facade of the resources a field points to (``facade:hasResourceFacade``):
    the class of resource it is a facade of, and the fields it exposes of each.
    None for a field whose values are plain text.
    """
    resource = graph.value(subject, _FACADE.hasResourceFacade)
    if not isinstance(resource, URIRef):
        return None

    resource_class = graph.value(resource, _FACADE.isFacadeOf)
    return {
        "resource_iri": str(resource_class) if resource_class is not None else None,
        "fields": sorted(
            (
                _read_field(graph, field_subject)
                for field_subject in graph.objects(resource, _FACADE.hasFacadeField)
                if isinstance(field_subject, URIRef)
            ),
            key=lambda declared: declared["order"],
        ),
    }


def _alternative_visualization(graph: Graph, subject: URIRef) -> dict[str, Any] | None:
    """
    The visualization a field asks for in place of plain text
    (``facade:hasAlternativeVisualization``) and the files it shows: the MIME
    types and extensions its file profile accepts. None for a field shown as text.

    The visualization and its profile are described in other ontologies of the
    package, so they are looked for there.
    """
    visualization = graph.value(subject, _FACADE.hasAlternativeVisualization)
    if not isinstance(visualization, URIRef):
        return None

    profile = _find(visualization, _FACADE.acceptsFileProfile)
    accepted: dict[str, list[str]] = {"mime_types": [], "extensions": []}
    if isinstance(profile, URIRef):
        accepted = {
            "mime_types": sorted(str(value) for value in _find_all(profile, _OBDC.acceptedMimeType)),
            "extensions": sorted(str(value) for value in _find_all(profile, _OBDC.acceptedExtension)),
        }

    return {
        "iri": str(visualization),
        "file_profile": str(profile) if profile is not None else None,
        "accepts": accepted,
    }


def _find_all(subject: URIRef, predicate: URIRef) -> list[Any]:
    """
    What the ontologies say about ``subject`` with ``predicate``. A file is
    parsed only when its text names both, which is read much faster than the
    file is parsed.
    """
    found: list[Any] = []
    for ontology_file in iter_ontology_files():
        text = ontology_cache.text(ontology_file)
        if _local_name(subject) in text and _local_name(predicate) in text:
            found.extend(ontology_cache.parsed(ontology_file).objects(subject, predicate))

    return found


def _find(subject: URIRef, predicate: URIRef) -> Any | None:
    values = _find_all(subject, predicate)
    return values[0] if values else None


def _deletable(graph: Graph, subject: URIRef) -> bool:
    """An instance can be deleted when the facade says so; a facade that does not say so forbids it."""
    if graph.value(subject, _FACADE.isDeletable) is None:
        return False

    return _flag(graph, subject, _FACADE.isDeletable)


def _commentable(graph: Graph, subject: URIRef) -> bool:
    """An instance can be commented on when the facade says so; a facade that does not say so forbids it."""
    if graph.value(subject, _FACADE.isCommentable) is None:
        return False

    return _flag(graph, subject, _FACADE.isCommentable)


def _options(graph: Graph, subject: URIRef) -> dict[str, Any]:
    """
    The values a field is chosen from, when its facade says they are the
    subclasses of a class: ``options`` has their identifiers and
    ``option_labels`` their names by lower-case language tag. Empty otherwise.
    """
    parent = graph.value(subject, _FACADE.hasValuesFromSubclassesOf)
    if not isinstance(parent, URIRef):
        return {"options": [], "option_labels": {}}

    options: dict[str, dict[str, str]] = {}
    for ontology_file in iter_ontology_files():
        text = ontology_cache.text(ontology_file)
        if "subClassOf" not in text or _local_name(parent) not in text:
            continue
        found = ontology_cache.parsed(ontology_file)
        for child in found.subjects(RDFS.subClassOf, parent):
            identifier = found.value(child, _DCTERMS.identifier)
            if not isinstance(identifier, Literal):
                continue
            options[str(identifier)] = {
                str(name.language).lower(): str(name)
                for name in found.objects(child, _SKOS.prefLabel)
                if isinstance(name, Literal) and name.language
            }

    return {"options": sorted(options), "option_labels": options}


def _creatable(graph: Graph, subject: URIRef) -> bool:
    """An instance can be created when the facade says so; one that does not say so cannot."""
    if graph.value(subject, _FACADE.isCreatable) is None:
        return False

    return _flag(graph, subject, _FACADE.isCreatable)


def _default(graph: Graph, subject: URIRef) -> str | None:
    """The IRI of the value generator that gives the field its value on creation, or None."""
    generator = graph.value(subject, _FACADE.hasDefault)
    return str(generator) if isinstance(generator, URIRef) else None


def _editable(graph: Graph, subject: URIRef) -> bool:
    """A field is editable when the facade says so; one that does not say so is not."""
    if graph.value(subject, _FACADE.isEditable) is None:
        return False

    return _flag(graph, subject, _FACADE.isEditable)


def _label(graph: Graph, subject: URIRef) -> str:
    labels = list(graph.objects(subject, _SCHEMA.name))
    for label in labels:
        if isinstance(label, Literal) and label.language == "en":
            return str(label)

    if not labels:
        raise ValueError(f"The facade declares no name for {subject}.")

    return str(labels[0])
