# BrasidataCenter

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

Brasidata's ontology collection, packaged for Python so every tool that consumes it — OntoBDC, InfoBIM, and others — gets the same deterministic set of RDF/Turtle sources after `pip install`, with no network fetch and no path guessing.

Browse the published ontologies at **[datacenter.app.br](https://datacenter.app.br)**. The Turtle sources under [`ontology/`](ontology/) are authoritative; the site is just a human-readable index of them.

## Repository layout

| Path | What it is |
| --- | --- |
| `ontology/` | The authoritative RDF/Turtle sources, grouped by domain. Currently: `domain/aeco` (core schema, geometry/IFC representation, kind/material taxonomy, catalog) and `domain/social`. |
| `src/brasidatacenter/` | The installable Python package: the resource API (`resources.py`) and the `brasidatacenter` CLI. |
| `kind_geometric_representation_mapping*.csv` | Reference mapping from AECO element kinds to their geometric representation (IFC class, predefined type, primitive), alongside `domain/aeco/taxonomy/kind.ttl`. |
| `legacy/` | Superseded tooling (e.g. the old OntoMaker ontology editor), kept for reference and not part of the installed package. |
| `index.html` | Source of the datacenter.app.br landing page. |

Only `ontology/`, `src/brasidatacenter/` and `README.md` ship to the production mirror this repository deploys to on release — everything else here is development-only.

## Install

```bash
pip install brasidatacenter
```

For local development, install this repository itself in editable mode:

```bash
./reinstall.sh   # or: pip install -e . --no-build-isolation
```

## Use

### As a resource API

```python
from brasidatacenter import ontology_root, ontology_path, iter_ontology_files

root = ontology_root()
aeco_schema = ontology_path("domain", "aeco", "core", "schema.ttl")

for resource in iter_ontology_files():
    print(resource)
```

`ontology_root()`, `ontology_path()` and `iter_ontology_files()` return `importlib.resources`-compatible `Traversable` objects, so callers never need to know whether the package was installed from a wheel or is running from this source checkout. During development, `ontology_root()` falls back to this repository's own `ontology/` tree, so files are never duplicated under `src/`.

### As a CLI

```bash
brasidatacenter --help
brasidatacenter tool
```

Commands are discovered by convention: any class under `src/brasidatacenter/<component>/plugin/command/` that implements `CommandPort` is picked up automatically and listed in `--help`. Adding a command is a matter of dropping a file in the right place, not registering it anywhere.

## License

Apache 2.0 — see [LICENSE](LICENSE).
