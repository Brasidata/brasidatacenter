"""Resolves the names people give an entity to the IRI of its type, from the ``ontobdc`` folder that holds them."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT_NAME: str = "ontobdc"
_MAPPING_PATH: tuple[str, ...] = ("mapping", "entity.yaml")


def ontobdc_directory(start: str | Path) -> Path:
    """
    The folder named ``ontobdc`` that ``start`` is in, or is: ``start`` is a folder of the file system, local or
    virtual, or a file in one, and the search goes up one level at a time from it.

    Raises:
        FileNotFoundError: ``start`` does not exist, or no folder of that name is found before the root of the
            file system, where there is no level left to go up to.
    """
    current: Path = Path(start).expanduser().resolve()
    if not current.exists():
        raise FileNotFoundError(f"{start} does not exist.")
    if current.is_file():
        current = current.parent

    while True:
        if current.name == ROOT_NAME and current.is_dir():
            return current

        parent: Path = current.parent
        if parent == current:
            raise FileNotFoundError(f"No folder named {ROOT_NAME} holds {start}, up to the root of the file system.")
        current = parent


def entity_names(start: str | Path) -> dict[str, str]:
    """
    The name -> IRI table of ``mapping/entity.yaml`` in the ``ontobdc`` folder found from ``start``, names in lower case.

    Raises:
        FileNotFoundError: no ``ontobdc`` folder is found, or the one found has no ``mapping/entity.yaml``.
        ValueError: the file does not hold an `ontology` mapping of names to IRIs.
    """
    mapping: Path = ontobdc_directory(start).joinpath(*_MAPPING_PATH)
    if not mapping.is_file():
        raise FileNotFoundError(f"The folder {mapping.parents[1]} has no {'/'.join(_MAPPING_PATH)}.")

    document = yaml.safe_load(mapping.read_text(encoding="utf-8"))
    table = document.get("ontology") if isinstance(document, dict) else None
    if not isinstance(table, dict) or not all(
        isinstance(name, str) and isinstance(iri, str) for name, iri in table.items()
    ):
        raise ValueError(f"{mapping} must hold an `ontology` mapping of names to IRIs.")
    return {name.casefold(): iri for name, iri in table.items()}


def entity_iri(start: str | Path, name: str) -> str | None:
    """
    The IRI of the entity type ``name`` stands for, ignoring case, in the mapping of the ``ontobdc`` folder found
    from ``start``; ``None`` when the mapping knows no such name.
    """
    return entity_names(start).get(name.casefold())
