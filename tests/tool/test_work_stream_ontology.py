from __future__ import annotations

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS, SDO

from brasidatacenter.resources import ontology_path

TYPE = Namespace(
    "http://datacenter.app.br/ontology/productivity/entity/work_stream/type.ttl#"
)
FACADE = Namespace(
    "http://datacenter.app.br/ontology/productivity/entity/work_stream/facade.ttl#"
)
OBDC = Namespace("http://ontobdc.org/ontology/domain/ontobdc/ns.ttl#")


def _parse(name: str) -> Graph:
    resource = ontology_path("tool", "ontobdc", "entity", name)
    with resource.open("rb") as stream:
        return Graph().parse(file=stream, format="turtle")


def test_work_stream_dimensions_are_unified_as_dimension_kinds() -> None:
    graph = _parse("work_stream_type.ttl")
    dimension_kinds = ("What", "Why", "Who", "Where", "When", "How", "HowMuch")

    assert not set(graph.subjects(RDF.type, OWL.DatatypeProperty))
    assert (TYPE.WorkStream, RDFS.subClassOf, OBDC.SurfaceableEntity) in graph
    assert (TYPE.WorkStream, RDF.type, OBDC.SurfaceableEntity) not in graph

    for local_name in dimension_kinds:
        dimension_kind = TYPE[local_name]
        assert (dimension_kind, RDF.type, TYPE.WorkStreamDimensionKind) in graph
        assert graph.value(dimension_kind, SDO.description) is not None

    for removed_property in ("what", "why", "who", "where", "when", "how", "howMuch"):
        assert not list(graph.triples((TYPE[removed_property], None, None)))


def test_facade_fields_map_to_dimension_kinds() -> None:
    graph = _parse("work_stream_facade.ttl")
    mappings = {
        "WhatField": "What",
        "WhyField": "Why",
        "WhoField": "Who",
        "WhereField": "Where",
        "WhenField": "When",
        "HowField": "How",
        "HowMuchField": "HowMuch",
    }

    assert (
        FACADE.mapsToDimensionKind,
        RDFS.range,
        TYPE.WorkStreamDimensionKind,
    ) in graph
    for field_name, kind_name in mappings.items():
        assert (
            FACADE[field_name],
            FACADE.mapsToDimensionKind,
            TYPE[kind_name],
        ) in graph
