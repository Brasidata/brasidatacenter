from __future__ import annotations

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS

from brasidatacenter.resources import ontology_path

VIEW = Namespace("http://datacenter.app.br/ontology/ontobdc/domain/view.ttl#")
EVENT = Namespace("http://datacenter.app.br/ontology/ontobdc/abox/presentation_event.ttl#")


def _parse_view_tbox() -> Graph:
    resource = ontology_path("tool", "ontobdc", "tbox", "view.ttl")
    with resource.open("rb") as stream:
        return Graph().parse(file=stream, format="turtle")


def _parse_presentation_event_policy() -> Graph:
    resource = ontology_path("tool", "ontobdc", "abox", "presentation_event.ttl")
    with resource.open("rb") as stream:
        return Graph().parse(file=stream, format="turtle")


def test_promotes_to_is_a_non_functional_object_property_between_presentation_events() -> None:
    graph = _parse_view_tbox()
    assert (VIEW.promotesTo, RDF.type, OWL.ObjectProperty) in graph
    assert (VIEW.promotesTo, RDF.type, OWL.FunctionalProperty) not in graph
    assert (VIEW.promotesTo, RDFS.domain, VIEW.PresentationEvent) in graph
    assert (VIEW.promotesTo, RDFS.range, VIEW.PresentationEvent) in graph


def test_component_event_and_shared_event_are_presentation_event_subclasses() -> None:
    graph = _parse_view_tbox()
    assert (VIEW.ComponentEvent, RDFS.subClassOf, VIEW.PresentationEvent) in graph
    assert (VIEW.SharedEvent, RDFS.subClassOf, VIEW.PresentationEvent) in graph


def test_every_promotion_subject_is_declared_a_component_event() -> None:
    graph = _parse_presentation_event_policy()
    subjects = set(graph.subjects(VIEW.promotesTo, None))
    assert subjects, "the policy must declare at least one promotion"
    for subject in subjects:
        assert (subject, RDF.type, VIEW.ComponentEvent) in graph


def test_every_promotion_target_is_declared_a_shared_event() -> None:
    graph = _parse_presentation_event_policy()
    targets = set(graph.objects(None, VIEW.promotesTo))
    assert targets, "the policy must declare at least one promotion target"
    for target in targets:
        assert (target, RDF.type, VIEW.SharedEvent) in graph


def test_component_file_single_click_has_no_promotion_target() -> None:
    graph = _parse_presentation_event_policy()
    assert (EVENT.ComponentFileSingleClick, RDF.type, VIEW.ComponentEvent) in graph
    assert not list(graph.objects(EVENT.ComponentFileSingleClick, VIEW.promotesTo))


def test_component_file_double_click_promotes_to_entity_page_requested() -> None:
    graph = _parse_presentation_event_policy()
    targets = list(graph.objects(EVENT.ComponentFileDoubleClick, VIEW.promotesTo))
    assert targets == [EVENT.EntityPageRequested]


def test_tile_opened_promotes_to_every_multivalued_target() -> None:
    graph = _parse_presentation_event_policy()
    targets = set(graph.objects(EVENT.TileOpened, VIEW.promotesTo))
    assert targets == {EVENT.TileReady, EVENT.SurfaceAreaFilled}


def test_all_event_subjects_and_promotion_targets_are_iris() -> None:
    graph = _parse_presentation_event_policy()
    component_events = list(graph.subjects(RDF.type, VIEW.ComponentEvent))
    shared_events = list(graph.subjects(RDF.type, VIEW.SharedEvent))
    assert component_events and shared_events
    for subject in component_events + shared_events:
        assert isinstance(subject, URIRef)
    for subject, target in graph.subject_objects(VIEW.promotesTo):
        assert isinstance(subject, URIRef)
        assert isinstance(target, URIRef)
