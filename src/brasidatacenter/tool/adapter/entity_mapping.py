"""Resolves the names people give an entity to the IRI of its type."""

from __future__ import annotations

from functools import lru_cache

import yaml

from brasidatacenter.resources import ontology_path

_MAPPING_PATH: tuple[str, ...] = ("tool", "ontobdc", "mapping", "entity.yaml")


@lru_cache(maxsize=1)
def _names() -> dict[str, str]:
    """The name -> IRI table of ``tool/ontobdc/mapping/entity.yaml``, names in lower case."""
    document = yaml.safe_load(ontology_path(*_MAPPING_PATH).read_text(encoding="utf-8"))
    table = document.get("ontology") if isinstance(document, dict) else None
    if not isinstance(table, dict) or not all(
        isinstance(name, str) and isinstance(iri, str) for name, iri in table.items()
    ):
        raise ValueError(f"{'/'.join(_MAPPING_PATH)} must hold an `ontology` mapping of names to IRIs.")
    return {name.casefold(): iri for name, iri in table.items()}


def entity_iri(name: str) -> str | None:
    """
    Return the IRI of the entity type ``name`` stands for, ignoring case, or
    ``None`` when the mapping knows no such name.
    """
    return _names().get(name.casefold())
