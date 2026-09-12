# OntoBDC infrastructure resource facades

This directory contains public projections of OntoBDC infrastructure resources.
`obdc:DataContainer` is an infrastructure resource; its facade is a
`facade:ResourceFacade`. `facade:DataEntityFacade` specializes that shared class
for data entities, whose facades remain under `../entity/`.

The shared vocabulary remains in
[`../../../old/ontobdc/domain/facade.ttl`](../../../old/ontobdc/domain/facade.ttl),
with its existing namespace `http://ontobdc.org/ontology/domain/facade.ttl#`.
`hasResourceFacade` is the inverse of `isFacadeOf`.
`hasDataEntityFacade` is a subproperty of `hasResourceFacade`, retaining its
`DataEntityFacade` range. The generic inverse must not infer that an
infrastructure resource's facade is a data entity facade.

`ResourceFacadeShape` validates the common target and field contract.
`DataEntityFacadeShape` delegates to it, including when validation runs without
RDFS or OWL inference. Existing field constraints apply to both kinds of facade.

## Data container

[`data_container_facade.ttl`](data_container_facade.ttl) projects the existing
class `http://ontobdc.org/ontology/domain/ontobdc/ns.ttl#DataContainer`, defined in
[`../tbox/ns.ttl`](../tbox/ns.ttl).

| Field | Projection datatype | RDF property | Order | Required | Editable |
| --- | --- | --- | ---: | --- | --- |
| `id` | `xsd:string` | `dcterms:identifier` | 10 | Yes | No |
| `title` | `xsd:string` | `dcterms:title` | 20 | Yes | Yes |
| `description` | `xsd:string` | `ct:description` | 30 | No | Yes |
| `location` | `xsd:anyURI` | `prov:atLocation` | 40 | Yes | No |
| `created_at` | `xsd:dateTime` | `ct:creationDate` | 50 | Yes | No |

All five fields are single-valued. The description is optional in the public
facade. Only title and description are editable; identifier, location, and
creation timestamp are read-only through this facade. Each field declares
identical `mapsToResource` and `mapsToProperty` values. `ct:` denotes
`http://standards.iso.org/iso/21597/-1/ed-1/en/Container#`.

`facade:isEditable` is a functional boolean property of `FacadeField`. Its shape
allows at most one boolean value and remains optional for existing facades.
The container facade declares an explicit value for every field.

The datatypes describe projected values. The source graph stores `location` as
an IRI and may store `title` and `description` as language-tagged literals.
A consumer writing RDF must preserve those node kinds and language tags;
`fieldDatatype` alone is not an instruction to replace the source RDF term.
The `id` field reads the literal `dcterms:identifier`, whose value also identifies
the container subject. Projecting the facade does not mint or change that identity.

The existing resource iterator discovers this file recursively, and the package
includes it through the ontology tree. Runtime consumers must use the generic
resource facade contract when handling infrastructure resources.
