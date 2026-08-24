from __future__ import annotations

from rdflib import Graph, Namespace
from rdflib.collection import Collection
from rdflib.namespace import OWL, RDF, RDFS, SDO

from brasidatacenter.resources import ontology_path

TYPE = Namespace(
    "http://datacenter.app.br/ontology/productivity/entity/work_stream/type.ttl#"
)
FACADE = Namespace(
    "http://datacenter.app.br/ontology/productivity/entity/work_stream/facade.ttl#"
)
FACADE_ONTOLOGY = Namespace("http://ontobdc.org/ontology/domain/facade.ttl#")
OBDC = Namespace("http://ontobdc.org/ontology/domain/ontobdc/ns.ttl#")
SH = Namespace("http://www.w3.org/ns/shacl#")


def _parse(name: str) -> Graph:
    resource = ontology_path("tool", "ontobdc", "entity", name)
    with resource.open("rb") as stream:
        return Graph().parse(file=stream, format="turtle")


def _parse_facade_ontology() -> Graph:
    resource = ontology_path("old", "ontobdc", "domain", "facade.ttl")
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

    key = graph.value(TYPE.WorkStreamDimension, OWL.hasKey)
    assert key is not None
    assert tuple(Collection(graph, key)) == (TYPE.dimensionOf, TYPE.dimensionKind)


def test_facade_contract_is_defined_in_the_shared_facade_ontology() -> None:
    graph = _parse_facade_ontology()

    assert (FACADE_ONTOLOGY.DataEntityFacade, RDF.type, OWL.Class) in graph
    assert (FACADE_ONTOLOGY.FacadeField, RDF.type, OWL.Class) in graph
    assert (
        FACADE_ONTOLOGY.fieldOrder,
        RDF.type,
        OWL.FunctionalProperty,
    ) in graph
    assert (
        FACADE_ONTOLOGY.mapsToResource,
        RDF.type,
        OWL.FunctionalProperty,
    ) in graph
    assert (
        FACADE_ONTOLOGY.FacadeFieldShape,
        RDF.type,
        SH.NodeShape,
    ) in graph


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
    assert (
        FACADE.mapsToDimensionKind,
        RDFS.subPropertyOf,
        FACADE_ONTOLOGY.mapsToResource,
    ) in graph
    for field_name, kind_name in mappings.items():
        assert (
            FACADE[field_name],
            FACADE.mapsToDimensionKind,
            TYPE[kind_name],
        ) in graph


def test_work_stream_facade_uses_shared_fields_in_declared_order() -> None:
    graph = _parse("work_stream_facade.ttl")
    expected_order = {
        "GlobalIdField": 10,
        "NameField": 20,
        "DescriptionField": 30,
        "WhatField": 40,
        "WhyField": 50,
        "WhoField": 60,
        "WhereField": 70,
        "WhenField": 80,
        "HowField": 90,
        "HowMuchField": 100,
    }

    assert (
        FACADE.DataEntityFacade,
        RDF.type,
        OWL.Class,
    ) not in graph
    assert (
        FACADE.FacadeField,
        RDF.type,
        OWL.Class,
    ) not in graph

    actual_orders = set()
    for field_name, order in expected_order.items():
        field = FACADE[field_name]
        assert (field, RDF.type, FACADE_ONTOLOGY.FacadeField) in graph
        for predicate in (
            SDO.identifier,
            FACADE_ONTOLOGY.fieldDatatype,
            FACADE_ONTOLOGY.fieldOrder,
            FACADE_ONTOLOGY.isRequired,
            FACADE_ONTOLOGY.isMultivalued,
            FACADE_ONTOLOGY.mapsToResource,
        ):
            assert len(list(graph.objects(field, predicate))) == 1

        actual_order = graph.value(field, FACADE_ONTOLOGY.fieldOrder).toPython()
        assert actual_order == order
        actual_orders.add(actual_order)

    assert len(actual_orders) == len(expected_order)
