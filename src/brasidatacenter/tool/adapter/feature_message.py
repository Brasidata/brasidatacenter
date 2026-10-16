"""Answers a presentation event's first messages from the feature ontology."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any

from rdflib import Graph

from brasidatacenter.resources import ontology_path

_FEATURE_PATH: tuple[str, ...] = ("tool", "ontobdc", "presentation")
_KNOWN_DEVICES = frozenset({"Desktop", "Mobile"})
_KNOWN_ENVIRONMENTS = frozenset({"Browser", "NativeApp"})
_VALUES_PATTERN = re.compile(
    r"VALUES\s*\(\?identifier\s+\?device\s+\?environment\s+\?language"
    r"(?:\s+\?hasDescription)?\)\s*\{.*?\}",
    re.DOTALL,
)


def first_message(
    identifier: str,
    device: str,
    environment: str,
    language: str,
    parameters: Mapping[str, str] | None = None,
) -> str | None:
    """
    Return the messages of the conversation ``identifier`` triggers for
    ``device``/``environment``, in ``language``, with placeholders filled from
    ``parameters``.

    Runs ``<identifier>_first_message.rq`` from the feature ontology directory,
    substituting its single-row ``VALUES`` block with the arguments given. When
    the query declares ``?hasDescription``, it is set to whether ``parameters``
    contains a non-empty ``description``.

    Returns all messages of the matched conversation joined by a blank line,
    with every declared placeholder replaced by its value in ``parameters``.
    Returns ``None`` when there is no such query, or it matches nothing.
    """
    if device not in _KNOWN_DEVICES:
        raise ValueError(f"Unknown device: {device!r}. Expected one of {sorted(_KNOWN_DEVICES)}.")
    if environment not in _KNOWN_ENVIRONMENTS:
        raise ValueError(
            f"Unknown environment: {environment!r}. Expected one of {sorted(_KNOWN_ENVIRONMENTS)}."
        )

    query_resource = ontology_path(*_FEATURE_PATH, f"{identifier}_first_message.rq")
    if not query_resource.is_file():
        return None

    parameters = dict(parameters or {})
    has_description = bool(parameters.get("description"))

    query_text = query_resource.read_text(encoding="utf-8")
    values_row = _build_values_row(identifier, device, environment, language, query_text, has_description)
    parameterized_query, replaced = _VALUES_PATTERN.subn(values_row, query_text, count=1)
    if replaced != 1:
        raise ValueError(
            f"{identifier}_first_message.rq has no single-row VALUES block to parameterize."
        )

    graph = Graph()
    for file_name in ("event.ttl", "ns.ttl"):
        resource = ontology_path(*_FEATURE_PATH, file_name)
        if resource.is_file():
            with resource.open("rb") as stream:
                graph.parse(file=stream, format="turtle")

    messages: list[tuple[int, str, list[str]]] = []
    for row in graph.query(parameterized_query):
        text = row["text"] if "text" in row.labels else None
        if text is None:
            continue
        index_value = row["index"] if "index" in row.labels else None
        index = int(index_value) if index_value is not None else 0
        parameters_value = row["parameters"] if "parameters" in row.labels else None
        required = _parse_parameters(parameters_value)
        messages.append((index, str(text), required))

    if not messages:
        return None

    messages.sort(key=lambda item: item[0])
    rendered = [_fill_template(text, required, parameters) for _, text, required in messages]
    return "\n\n".join(rendered)


def _build_values_row(
    identifier: str,
    device: str,
    environment: str,
    language: str,
    query_text: str,
    has_description: bool,
) -> str:
    variables = "?identifier ?device ?environment ?language"
    values = (
        f'("{_escape_literal(identifier)}" :{device} :{environment} '
        f'"{_escape_literal(language)}"'
    )
    if "?hasDescription" in query_text:
        variables += " ?hasDescription"
        values += f" {str(has_description).lower()}"
    values += ")"
    return f"VALUES ({variables}) {{ {values} }}"


def _parse_parameters(raw: Any) -> list[str]:
    if raw is None:
        return []
    value = str(raw)
    return [name for name in value.split(",") if name]


def _fill_template(
    template: str,
    required: list[str],
    provided: Mapping[str, str],
) -> str:
    missing = [name for name in required if name not in provided]
    if missing:
        raise KeyError(f"Message template requires missing parameters: {missing}")
    return template.format_map(_SafeMapping(provided))


class _SafeMapping(Mapping[str, str]):
    """Leaves undeclared placeholders untouched instead of raising KeyError."""

    def __init__(self, data: Mapping[str, str]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> str:
        return self._data.get(key, "{" + key + "}")

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __len__(self) -> int:
        return len(self._data)


def _escape_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
