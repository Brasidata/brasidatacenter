# ifc4_owl.ttl

The ifcOWL ontology of IFC4 (FINAL), as generated from the EXPRESS schema by the IFC-to-RDF converter of
Pieter Pauwels, Jyrki Oraskari and Davy Van Deursen, and published by the converter project
(`pipauwel/IFCtoRDF`, `src/main/resources/IFC4.ttl`). It is the ontology of the namespace
`https://standards.buildingsmart.org/IFC/DEV/IFC4/FINAL/OWL#` that `domain/aeco/representation/bsi_ifc.ttl` binds to.
The file is kept as it was published (its namespace is written with `http`).

License: [Creative Commons Attribution 3.0](http://creativecommons.org/licenses/by/3.0/), as the file declares
(`cc:license`). Creators: Pieter Pauwels and Walter Terkaj; contributors: Jakob Beetz, Aleksandra Sojic and
Maria Poveda Villalon.

It is not an ontology of the `ontology/` tree on purpose: the files of that tree are all parsed when the facades are
looked for, and this one is large. It is read only by `brasidatacenter.tool.adapter.class_definition`, which scans its
text for the class that was asked about.

# adiro_domain_common_disciplines.ttl

The discipline classes of ADIRO Domain Common 4.0.0 (`Discipline` and its subclasses: `Architectural`, `Facade`,
`Structural`, `MEP`, `Mechanical`, `Electrical`, `Plumbing`, `Lighting`, `FireLifeSafety`, `Masterplan` and `Civil`), the
ontology of the namespace `https://w3id.org/adiro/adiro_domain_common#`, published by Buro Happold - Machine Learning
R&D (`BuroHappoldMachineLearning/ADIRO`, `src/adiro_domain_common.ttl`). The declarations of the classes are as they were
published; the restriction that ties them to the `Layout` of the drawing metadata was left out.

License: [GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.html), as the ontology declares
(`dcterms:license`). It keeps that license, which is not the one of this repository.

`domain/aeco/taxonomy/type.ttl` refers to `adiro:Discipline` by its namespace; nothing reads this file as part of the
`ontology/` tree.
