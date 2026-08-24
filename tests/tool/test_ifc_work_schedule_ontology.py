from __future__ import annotations

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS, SDO

from brasidatacenter.resources import ontology_path

IBIM = Namespace("https://infobim.org/ontology/ns#")
OBDC = Namespace("http://ontobdc.org/ontology/domain/ontobdc/ns.ttl#")
IFCOWL = Namespace(
    "https://standards.buildingsmart.org/IFC/DEV/IFC4/FINAL/OWL#"
)


def _parse() -> Graph:
    resource = ontology_path(
        "tool",
        "infobim",
        "entity",
        "ifc_work_schedule_type.ttl",
    )
    with resource.open("rb") as stream:
        return Graph().parse(file=stream, format="turtle")


def test_ifc_work_schedule_uses_the_work_stream_dimension_structure() -> None:
    graph = _parse()

    assert (IBIM.IfcWorkSchedule, RDF.type, OWL.Class) in graph
    assert (IBIM.IfcWorkSchedule, RDFS.subClassOf, OBDC.SurfaceableEntity) in graph
    assert (IBIM.IfcWorkSchedule, RDFS.subClassOf, IFCOWL.IfcWorkSchedule) in graph
    assert (
        IBIM.IfcWorkScheduleDimension,
        RDFS.subClassOf,
        OBDC.DataEntity,
    ) in graph
    assert (IBIM.hasDimension, RDFS.domain, IBIM.IfcWorkSchedule) in graph
    assert (
        IBIM.hasDimension,
        RDFS.range,
        IBIM.IfcWorkScheduleDimension,
    ) in graph
    assert (
        IBIM.dimensionKind,
        RDFS.range,
        IBIM.IfcWorkScheduleDimensionKind,
    ) in graph
    assert not set(graph.subjects(RDF.type, OWL.DatatypeProperty))


def test_ifc_work_schedule_declares_gantt_control_dimension_kinds() -> None:
    graph = _parse()
    expected_kinds = {
        "ScopePlanned",
        "ScopeActual",
        "TimePlanned",
        "TimeActual",
        "TimeForecast",
        "ProgressPlanned",
        "ProgressActual",
        "ProgressForecast",
        "LaborPlanned",
        "LaborActual",
        "EquipmentPlanned",
        "EquipmentActual",
        "MaterialPlanned",
        "MaterialActual",
        "CostPlanned",
        "CostActual",
        "CostForecast",
    }
    actual_kinds = {
        str(subject).removeprefix(str(IBIM))
        for subject in graph.subjects(
            RDF.type,
            IBIM.IfcWorkScheduleDimensionKind,
        )
    }

    assert actual_kinds == expected_kinds
    assert (IBIM.Gantt, RDFS.subClassOf, OBDC.ProjectManagementFramework) in graph
    assert str(graph.value(IBIM.Gantt, SDO.identifier)) == "gantt"
