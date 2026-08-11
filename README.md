# BrasidataCenter

BrasidataCenter distributes the Brasidata ontology tree as a versioned Python package.

The repository keeps ontology sources under `ontology/`. During wheel creation, that tree is packaged inside `brasidatacenter/ontology`, allowing OntoBDC and other consumers to resolve a deterministic local ontology set after `pip install`.

## Install

```bash
pip install brasidatacenter
```

## Python API

```python
from brasidatacenter import ontology_root, ontology_path, iter_ontology_files

root = ontology_root()
person_type = ontology_path("social", "entity", "person", "type.ttl")

for resource in iter_ontology_files():
    print(resource)
```

The helpers return `importlib.resources`-compatible `Traversable` resources so consumers do not need to know where the package was installed.

## Intended OntoBDC integration

OntoBDC should depend on a compatible BrasidataCenter release (directly or through a Python extra), resolve ontologies from the installed package, and embed/copy only the required ontology resources into generated standalone artifacts.

Example future dependency composition:

```toml
[project.optional-dependencies]
brasidatacenter = [
  "brasidatacenter>=0.1,<0.2"
]
```

Then:

```bash
pip install "ontobdc[brasidatacenter]"
```

## Development

```bash
python -m pip install -e ".[dev]"
pytest
```

The resource API falls back to the repository-root `ontology/` tree during development, so ontology files do not need to be duplicated under `src/`.

## Build and validate a release

```bash
python -m pip install -U build twine
python -m build
python -m twine check dist/*
```

Inspect the built wheel before publishing if desired:

```bash
python -m zipfile -l dist/*.whl
```

The wheel must contain the ontology tree under `brasidatacenter/ontology/`.

Publish to TestPyPI first if desired, then PyPI using your normal credentials or Trusted Publishing workflow.

## Versioning

The Python distribution has its own version lifecycle. OntoBDC should depend on compatible version ranges rather than assuming the ontology package always shares the OntoBDC version.
