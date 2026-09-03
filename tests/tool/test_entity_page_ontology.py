from __future__ import annotations

from rdflib import Graph, Namespace
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SDO

from brasidatacenter.resources import ontology_path


VIEW = Namespace("http://datacenter.app.br/ontology/ontobdc/domain/view.ttl#")
OBDC = Namespace("http://ontobdc.org/ontology/domain/ontobdc/ns.ttl#")
ENTITY_PAGE = Namespace(
    "http://datacenter.app.br/ontology/ontobdc/abox/entity_page.ttl#"
)
WORK_STREAM = Namespace(
    "http://datacenter.app.br/ontology/productivity/entity/work_stream/type.ttl#"
)
INFOBIM_ENTITY_PAGE = Namespace(
    "https://infobim.org/ontology/abox/entity_page.ttl#"
)
IBIM = Namespace("https://infobim.org/ontology/ns#")


def _parse(*parts: str) -> Graph:
    resource = ontology_path(*parts)
    with resource.open("rb") as stream:
        return Graph().parse(file=stream, format="turtle")


def test_entity_instance_and_entity_type_relations_are_distinct() -> None:
    graph = _parse("tool", "ontobdc", "tbox", "view.ttl")

    assert (VIEW.presentsEntity, RDFS.range, OBDC.DataEntity) in graph
    assert (VIEW.presentsEntityType, RDF.type, OWL.ObjectProperty) in graph
    assert (VIEW.presentsEntityType, RDFS.domain, VIEW.EntityPage) in graph
    assert (VIEW.presentsEntityType, RDFS.range, OWL.Class) in graph


def test_work_stream_page_declares_the_supported_entity_type() -> None:
    graph = _parse("tool", "ontobdc", "abox", "entity_page.ttl")

    assert (ENTITY_PAGE.WorkStreamPage, RDF.type, VIEW.EntityPage) in graph
    assert (
        ENTITY_PAGE.WorkStreamPage,
        VIEW.presentsEntityType,
        WORK_STREAM.WorkStream,
    ) in graph
    assert (
        ENTITY_PAGE.WorkStreamPage,
        VIEW.presentsEntity,
        WORK_STREAM.WorkStream,
    ) not in graph
    assert str(graph.value(ENTITY_PAGE.WorkStreamPage, SDO.identifier)) == (
        "work_stream"
    )
    assert (
        ENTITY_PAGE.WorkStreamToolbar,
        RDF.type,
        VIEW.EntityPageToolbar,
    ) in graph
    assert (
        ENTITY_PAGE.WorkStreamToolbar,
        DCTERMS.isPartOf,
        ENTITY_PAGE.WorkStreamPage,
    ) in graph


def test_ifc_work_schedule_page_declares_the_supported_entity_type() -> None:
    graph = _parse("tool", "infobim", "abox", "entity_page.ttl")

    assert (
        INFOBIM_ENTITY_PAGE.IfcWorkSchedulePage,
        RDF.type,
        VIEW.EntityPage,
    ) in graph
    assert (
        INFOBIM_ENTITY_PAGE.IfcWorkSchedulePage,
        VIEW.presentsEntityType,
        IBIM.IfcWorkSchedule,
    ) in graph
    assert str(
        graph.value(INFOBIM_ENTITY_PAGE.IfcWorkSchedulePage, SDO.identifier)
    ) == "ifc_work_schedule"
    assert (
        INFOBIM_ENTITY_PAGE.IfcWorkScheduleToolbar,
        RDF.type,
        VIEW.EntityPageToolbar,
    ) in graph
    assert (
        INFOBIM_ENTITY_PAGE.IfcWorkScheduleToolbar,
        DCTERMS.isPartOf,
        INFOBIM_ENTITY_PAGE.IfcWorkSchedulePage,
    ) in graph
