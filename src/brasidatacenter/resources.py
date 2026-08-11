from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Iterable, Iterator

_DEFAULT_SUFFIXES = (".ttl", ".owl", ".rdf", ".jsonld", ".json")


def ontology_root() -> Traversable:
    """Return the root of the ontology tree.

    In an installed wheel the ontology tree is packaged under
    ``brasidatacenter/ontology``. During repository development, fall back to
    the source ``ontology/`` directory at the repository root.
    """
    packaged = files("brasidatacenter").joinpath("ontology")
    if packaged.is_dir():
        return packaged

    development = Path(__file__).resolve().parents[2] / "ontology"
    if development.is_dir():
        return development

    raise FileNotFoundError("BrasidataCenter ontology resources were not found")


def ontology_path(*parts: str) -> Traversable:
    """Return a resource within the ontology tree."""
    resource = ontology_root()
    for part in parts:
        resource = resource.joinpath(part)
    return resource


def iter_ontology_files(
    suffixes: Iterable[str] = _DEFAULT_SUFFIXES,
) -> Iterator[Traversable]:
    """Recursively iterate ontology files included in the distribution."""
    accepted = {suffix.lower() for suffix in suffixes}

    def walk(node: Traversable) -> Iterator[Traversable]:
        for child in node.iterdir():
            if child.is_dir():
                yield from walk(child)
            elif not accepted or Path(child.name).suffix.lower() in accepted:
                yield child

    yield from walk(ontology_root())
