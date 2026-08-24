from __future__ import annotations

from rdflib import Graph, Namespace
from rdflib.namespace import OWL, RDF, RDFS, SDO

from brasidatacenter.resources import ontology_path

IBIM = Namespace("https://infobim.org/ontology/ns#")
OBDC = Namespace("http://ontobdc.org/ontology/domain/ontobdc/ns.ttl#")
FACADE = Namespace(
    "https://infobim.org/ontology/entity/ifc_work_schedule/facade.ttl#"
)
FACADE_ONTOLOGY = Namespace("http://ontobdc.org/ontology/domain/facade.ttl#")
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


def _parse_facade() -> Graph:
    resource = ontology_path(
        "tool",
        "infobim",
        "entity",
        "ifc_work_schedule_facade.ttl",
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


def test_ifc_work_schedule_facade_uses_the_shared_contract() -> None:
    graph = _parse_facade()
    fields = set(
        graph.objects(
            FACADE.IfcWorkScheduleFacade,
            FACADE_ONTOLOGY.hasFacadeField,
        )
    )

    assert (
        FACADE.IfcWorkScheduleFacade,
        RDF.type,
        FACADE_ONTOLOGY.DataEntityFacade,
    ) in graph
    assert len(fields) == 30
    assert (
        FACADE.FacadeField,
        RDF.type,
        OWL.Class,
    ) not in graph

    orders = set()
    for field in fields:
        assert (field, RDF.type, FACADE_ONTOLOGY.FacadeField) in graph
        for predicate in (
            SDO.identifier,
            FACADE_ONTOLOGY.fieldDatatype,
            FACADE_ONTOLOGY.fieldOrder,
            FACADE_ONTOLOGY.mapsToResource,
            FACADE_ONTOLOGY.isRequired,
            FACADE_ONTOLOGY.isMultivalued,
        ):
            assert len(list(graph.objects(field, predicate))) == 1
        orders.add(graph.value(field, FACADE_ONTOLOGY.fieldOrder).toPython())

    assert orders == set(range(10, 301, 10))


def test_ifc_work_schedule_facade_maps_canonical_ifc_attributes() -> None:
    graph = _parse_facade()
    mappings = {
        "GlobalIdField": (IFCOWL.globalId_IfcRoot, IFCOWL.IfcRoot, "GlobalId"),
        "NameField": (IFCOWL.name_IfcRoot, IFCOWL.IfcRoot, "Name"),
        "DescriptionField": (
            IFCOWL.description_IfcRoot,
            IFCOWL.IfcRoot,
            "Description",
        ),
        "ObjectTypeField": (
            IFCOWL.objectType_IfcObject,
            IFCOWL.IfcObject,
            "ObjectType",
        ),
        "IdentificationField": (
            IFCOWL.identification_IfcControl,
            IFCOWL.IfcControl,
            "Identification",
        ),
        "CreationDateField": (
            IFCOWL.creationDate_IfcWorkControl,
            IFCOWL.IfcWorkControl,
            "CreationDate",
        ),
        "CreatorsField": (
            IFCOWL.creators_IfcWorkControl,
            IFCOWL.IfcWorkControl,
            "Creators",
        ),
        "PurposeField": (
            IFCOWL.purpose_IfcWorkControl,
            IFCOWL.IfcWorkControl,
            "Purpose",
        ),
        "DurationField": (
            IFCOWL.duration_IfcWorkControl,
            IFCOWL.IfcWorkControl,
            "Duration",
        ),
        "TotalFloatField": (
            IFCOWL.totalFloat_IfcWorkControl,
            IFCOWL.IfcWorkControl,
            "TotalFloat",
        ),
        "StartTimeField": (
            IFCOWL.startTime_IfcWorkControl,
            IFCOWL.IfcWorkControl,
            "StartTime",
        ),
        "FinishTimeField": (
            IFCOWL.finishTime_IfcWorkControl,
            IFCOWL.IfcWorkControl,
            "FinishTime",
        ),
        "PredefinedTypeField": (
            IFCOWL.predefinedType_IfcWorkSchedule,
            IFCOWL.IfcWorkSchedule,
            "PredefinedType",
        ),
    }

    for field_name, (property_iri, owner_class, attribute_name) in mappings.items():
        field = FACADE[field_name]
        assert (field, FACADE_ONTOLOGY.mapsToProperty, property_iri) in graph
        assert (field, FACADE.propertyOwnerClass, owner_class) in graph
        assert str(graph.value(field, FACADE.ifcAttributeName)) == attribute_name


def test_ifc_work_schedule_facade_maps_all_control_dimensions() -> None:
    graph = _parse_facade()
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
        str(kind).removeprefix(str(IBIM))
        for kind in graph.objects(None, FACADE.mapsToDimensionKind)
    }
    assert actual_kinds == expected_kinds

    for kind_name in expected_kinds:
        field = FACADE[f"{kind_name}Field"]
        assert (
            field,
            FACADE_ONTOLOGY.mapsToResource,
            IBIM[kind_name],
        ) in graph
