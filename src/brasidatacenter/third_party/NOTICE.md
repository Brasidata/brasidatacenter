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
