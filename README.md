# BrasidataCenter

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Brasidata's ontology collection — social, productivity, and sales domains — packaged for Python so OntoBDC and other tools get a deterministic local ontology set after `pip install`.

Browse the ontologies at **[datacenter.app.br](https://datacenter.app.br)**. The Turtle sources under `ontology/` are authoritative; the site is a human-readable index of them.

## Install

```bash
pip install brasidatacenter
```

## Use

```python
from brasidatacenter import ontology_root, ontology_path, iter_ontology_files

root = ontology_root()
person_type = ontology_path("social", "entity", "person", "type.ttl")

for resource in iter_ontology_files():
    print(resource)
```

These return `importlib.resources`-compatible `Traversable` objects, so callers never need to know where the package was installed.

The resource API falls back to the repository-root `ontology/` tree during development, so files don't need to be duplicated under `src/`.
