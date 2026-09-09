from __future__ import annotations

import pytest
from pyshacl import validate
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import DCTERMS, PROV, RDF, RDFS, SDO, XSD

from brasidatacenter.resources import iter_ontology_files, ontology_path

FACADE = Namespace("http://ontobdc.org/ontology/domain/facade.ttl#")
CONTAINER = Namespace(
    "http://datacenter.app.br/ontology/tool/ontobdc/resource/data_container_facade.ttl#"
)
OBDC = Namespace("http://ontobdc.org/ontology/domain/ontobdc/ns.ttl#")
CT = Namespace("http://standards.iso.org/iso/21597/-1/ed-1/en/Container#")
SH = Namespace("http://www.w3.org/ns/shacl#")
CONTAINER_PATH = "tool/ontobdc/resource/data_container_facade.ttl"


def _parse(path: str) -> Graph:
    with ontology_path(*path.split("/")).open("rb") as stream:
        return Graph().parse(file=stream, format="turtle")


def _vocabulary() -> Graph:
    return _parse("old/ontobdc/domain/facade.ttl")


def test_container_facade_stays_an_infrastructure_resource_after_inference() -> None:
    vocabulary = _vocabulary()
    graph = (
        vocabulary
        + _parse("tool/ontobdc/tbox/ns.ttl")
        + _parse(CONTAINER_PATH)
    )
    conforms, _, report = validate(
        graph, shacl_graph=vocabulary, inference="owlrl", inplace=True
    )
    assert conforms, report
    assert (CONTAINER.DataContainerFacade, RDF.type, FACADE.ResourceFacade) in graph
    assert (CONTAINER.DataContainerFacade, RDF.type, FACADE.DataEntityFacade) not in graph
    assert (OBDC.DataContainer, RDF.type, OBDC.DataEntity) not in graph
    assert (OBDC.DataContainer, RDFS.subClassOf, OBDC.DataEntity) not in graph
    assert (OBDC.DataContainer, FACADE.hasDataEntityFacade, CONTAINER.DataContainerFacade) not in graph


@pytest.mark.parametrize(
    "path",
    [
        "tool/ontobdc/entity/work_stream_facade.ttl",
        "tool/infobim/entity/ifc_work_schedule_facade.ttl",
    ],
)
def test_existing_entity_facades_keep_their_contract_and_gain_resource_discovery(
    path: str,
) -> None:
    vocabulary = _vocabulary()
    source = _parse(path)
    graph = source + vocabulary
    conforms, _, report = validate(
        graph, shacl_graph=vocabulary, inference="owlrl", inplace=True
    )
    assert conforms, report
    entity_facades = list(source.subject_objects(FACADE.hasDataEntityFacade))
    assert entity_facades
    for resource_class, facade in entity_facades:
        assert (resource_class, FACADE.hasDataEntityFacade, facade) in graph
        assert (resource_class, FACADE.hasResourceFacade, facade) in graph
        assert (facade, RDF.type, FACADE.DataEntityFacade) in graph
        assert (facade, RDF.type, FACADE.ResourceFacade) in graph


@pytest.mark.parametrize("facade_type", [FACADE.ResourceFacade, FACADE.DataEntityFacade])
@pytest.mark.parametrize("missing_property", [FACADE.isFacadeOf, FACADE.hasFacadeField])
def test_resource_and_entity_facades_require_a_target_and_fields_without_inference(
    facade_type, missing_property,
) -> None:
    graph = _parse(CONTAINER_PATH)
    graph.set((CONTAINER.DataContainerFacade, RDF.type, facade_type))
    graph.remove((CONTAINER.DataContainerFacade, missing_property, None))
    conforms, results, _ = validate(graph, shacl_graph=_vocabulary(), inference="none")
    assert not conforms
    assert list(results.subjects(SH.focusNode, CONTAINER.DataContainerFacade))


@pytest.mark.parametrize("missing_property", [FACADE.fieldDatatype, FACADE.mapsToResource])
def test_resource_fields_retain_required_datatype_and_mapping(missing_property) -> None:
    graph = _parse(CONTAINER_PATH)
    graph.remove((CONTAINER.LocationField, missing_property, None))
    conforms, results, _ = validate(graph, shacl_graph=_vocabulary(), inference="none")
    assert not conforms
    assert list(results.subjects(SH.focusNode, CONTAINER.LocationField))


def test_conflicting_property_mapping_is_rejected() -> None:
    graph = _parse(CONTAINER_PATH)
    graph.set((CONTAINER.DescriptionField, FACADE.mapsToProperty, DCTERMS.description))
    conforms, results, _ = validate(graph, shacl_graph=_vocabulary(), inference="none")
    assert not conforms
    assert list(results.subjects(SH.focusNode, CONTAINER.DescriptionField))


@pytest.mark.parametrize("values", [[Literal("yes")], [Literal(True), Literal(False)]])
def test_editability_must_be_a_single_boolean(values) -> None:
    graph = _parse(CONTAINER_PATH)
    graph.remove((CONTAINER.TitleField, FACADE.isEditable, None))
    for value in values:
        graph.add((CONTAINER.TitleField, FACADE.isEditable, value))
    conforms, results, _ = validate(graph, shacl_graph=_vocabulary(), inference="none")
    assert not conforms
    assert any(
        (result, SH.resultPath, FACADE.isEditable) in results
        for result in results.subjects(SH.focusNode, CONTAINER.TitleField)
    )


def test_container_projection_matches_storage_metadata_and_is_discoverable() -> None:
    graph = _parse(CONTAINER_PATH)
    expected = {
        "id": (XSD.string, DCTERMS.identifier, 10),
        "title": (XSD.string, DCTERMS.title, 20),
        "description": (XSD.string, CT.description, 30),
        "location": (XSD.anyURI, PROV.atLocation, 40),
        "created_at": (XSD.dateTime, CT.creationDate, 50),
    }
    fields = list(graph.objects(CONTAINER.DataContainerFacade, FACADE.hasFacadeField))
    assert len(fields) == len(expected)
    actual = {}
    for field in fields:
        name = str(graph.value(field, SDO.identifier))
        actual[name] = (
            graph.value(field, FACADE.fieldDatatype),
            graph.value(field, FACADE.mapsToProperty),
            graph.value(field, FACADE.fieldOrder).toPython(),
        )
        assert graph.value(field, FACADE.mapsToResource) == graph.value(field, FACADE.mapsToProperty)
        assert graph.value(field, FACADE.isRequired) == Literal(name != "description")
        assert graph.value(field, FACADE.isMultivalued) == Literal(False)
        assert list(graph.objects(field, FACADE.isEditable)) == [
            Literal(name in {"title", "description"})
        ]
    assert actual == expected
    assert (CONTAINER.DataContainerFacade, FACADE.isFacadeOf, OBDC.DataContainer) in graph
    assert (OBDC.DataContainer, FACADE.hasResourceFacade, CONTAINER.DataContainerFacade) in graph
    assert any(resource.name == "data_container_facade.ttl" for resource in iter_ontology_files())
