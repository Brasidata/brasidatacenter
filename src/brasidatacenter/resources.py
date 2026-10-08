from __future__ import annotations

from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Iterable, Iterator

_DEFAULT_SUFFIXES = (".ttl", ".owl", ".rdf", ".jsonld", ".json")

#: Where the ontologies of this package are published (the GitHub Pages
#: site of the production repository): the IRI of an ontology is this base
#: followed by the path of its file under ``ontology/``.
ONTOLOGY_BASE_IRI = "http://datacenter.app.br/ontology/"


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


def ontology_path_for_iri(iri: str) -> Traversable:
    """Return the file of the ontology published at ``iri``.

    The IRI of an ontology, or of any term in it (``...#Term``), names its
    file: ``ONTOLOGY_BASE_IRI`` followed by the file's path under
    ``ontology/``.

    Raises:
        ValueError: ``iri`` is not under ``ONTOLOGY_BASE_IRI``.
        FileNotFoundError: this package has no file for ``iri``.
    """
    if not iri.startswith(ONTOLOGY_BASE_IRI):
        raise ValueError(f"{iri} is not a BrasidataCenter ontology IRI (they start with {ONTOLOGY_BASE_IRI}).")
    relative = iri[len(ONTOLOGY_BASE_IRI):].split("#", 1)[0]
    resource = ontology_path(*relative.split("/"))
    if not resource.is_file():
        raise FileNotFoundError(f"This brasidatacenter package has no ontology file for {iri} (ontology/{relative}).")
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
