import os
from typing import Any, ClassVar, Dict, List, Optional, Union

from ontobdc.cli.domain.port.command import CliCommandPort
from ontobdc.cli.domain.model.command import CliCommandMetadata
from ontobdc.cli.domain.request.command import CliCommandRequest
from ontobdc.cli.domain.response.command import CommandResponse

from cockpit.rclone.adapter.discovery import (
    discover_rclone_processes,
    discover_sync_logs,
    format_age_human,
    parse_process,
    read_sync_progress,
)


_FRIENDLY_NAMES: Dict[str, str] = {
    "brasidata": "Root (My Drive)",
    "brasidata_shared_brasidata": "Shared Brasidata",
    "brasidata_shared_brasibim": "Shared BrasiBIM",
}


def _friendly_sync_name(remote: str, local_path: str) -> str:
    if not remote:
        return os.path.basename(local_path) if local_path else "unknown"
    remote_prefix: str = remote.split(":", 1)[0]
    if remote_prefix in _FRIENDLY_NAMES:
        return _FRIENDLY_NAMES[remote_prefix]
    local_base: str = os.path.basename(local_path) if local_path else ""
    if local_base:
        return "{} \u00b7 {}".format(remote_prefix, local_base)
    return remote_prefix


def _quantity_cell(progress: Dict[str, Any]) -> str:
    items_done: Optional[int] = progress.get("transferred_items_done")
    items_total: Optional[int] = progress.get("transferred_items_total")
    if items_done is not None or items_total is not None:
        done: Any = items_done if items_done is not None else "?"
        total: Any = items_total if items_total is not None else "?"
        return "{} / {}".format(done, total)
    bytes_raw: Any = progress.get("transferred_bytes")
    if bytes_raw:
        return str(bytes_raw)
    return "-"


def _percentage_cell(progress: Dict[str, Any]) -> str:
    items_pct: Any = progress.get("transferred_items_pct")
    if items_pct:
        return str(items_pct)
    bytes_pct: Any = progress.get("transferred_bytes_pct")
    if bytes_pct:
        return str(bytes_pct)
    return "-"


def _last_update_age(progress: Dict[str, Any]) -> str:
    age: Optional[Union[int, float]] = progress.get("last_logline_age_seconds")
    if age is None:
        age = progress.get("log_mtime_age_seconds")
    if age is None:
        age = progress.get("last_progress_items_age_seconds")
    if age is None:
        age = progress.get("last_progress_bytes_age_seconds")
    return format_age_human(age)


def _render_table_lines(headers: List[str], rows: List[List[str]]) -> List[str]:
    if not headers:
        return []

    all_rows: List[List[str]] = [headers, *rows]
    n_cols: int = len(headers)
    widths: List[int] = [0] * n_cols
    r: List[str]
    for r in all_rows:
        padded: List[str] = list(r) + [""] * (n_cols - len(r))
        i: int
        cell: str
        for i, cell in enumerate(padded[:n_cols]):
            widths[i] = max(widths[i], len(str(cell)))

    gutter: str = "   "
    lines: List[str] = []

    header_cells: List[str] = []
    separator_cells: List[str] = []
    idx: int
    for idx in range(n_cols):
        raw_header: str = str(headers[idx]) if idx < len(headers) else ""
        header_cells.append(raw_header.ljust(widths[idx]))
        separator_cells.append("\u2500" * widths[idx])

    lines.append(gutter.join(header_cells))
    lines.append(gutter.join(separator_cells))

    for row in rows:
        body_cells: List[str] = []
        j: int
        for j in range(n_cols):
            raw: str = str(row[j]) if j < len(row) else ""
            body_cells.append(raw.ljust(widths[j]))
        lines.append(gutter.join(body_cells))

    return lines


class RcloneSyncsCommand(CliCommandPort):
    METADATA: CliCommandMetadata = CliCommandMetadata(
        id="rclone_syncs",
        logical_component="rclone",
        description=(
            "Per-process sync-progress snapshot read from each "
            "rclone process's log file."
        ),
        depends_on=None,
        arguments=[
            {
                "accepts": ["--syncs"],
                "description": (
                    "Show a real-time transfer progress snapshot for "
                    "every live rclone process that uses an explicit "
                    "``--log-file``."
                ),
                "usage": "cockpit rclone --syncs",
            },
        ],
    )

    COMPONENT: ClassVar[str] = "rclone"
    FLAG: ClassVar[str] = "--syncs"

    @staticmethod
    def accepts(args: List[str]) -> bool:
        if not args or args[0] != RcloneSyncsCommand.COMPONENT:
            return False
        scoped: List[str] = args[1:]
        if not scoped:
            return True
        return RcloneSyncsCommand.FLAG in scoped

    def __init__(self, request: CliCommandRequest) -> None:
        self._request: CliCommandRequest = request

    def check(self) -> bool:
        return self.__class__.accepts(
            [self.__class__.COMPONENT, *self._request.command_args]
        )

    def run(self) -> CommandResponse:
        live_parsed: List[Dict[str, Any]] = [
            parse_process(p) for p in discover_rclone_processes()
        ]
        recent_logs: List[Dict[str, Any]] = discover_sync_logs(only_recent_hours=24)

        seen_log_files: set = set()
        merged: List[Dict[str, Any]] = []
        proc: Dict[str, Any]
        for proc in live_parsed:
            log_key: str = str(proc.get("log_file") or "")
            if log_key:
                seen_log_files.add(log_key)
            merged.append(proc)
        for proc in recent_logs:
            log_key = str(proc.get("log_file") or "")
            if log_key and log_key in seen_log_files:
                continue
            if log_key:
                seen_log_files.add(log_key)
            merged.append(proc)

        headers: List[str] = [
            "Nome do sync",
            "Quantidade",
            "Porcentagem",
            "\u00daltima atualiza\u00e7\u00e3o",
        ]
        rows: List[List[str]] = []

        for proc in merged:
            log_file: str = proc.get("log_file") or ""
            if not log_file:
                continue

            progress: Dict[str, Any] = read_sync_progress(log_file) or {}
            friendly_spec: Any = proc.get("friendly_name")
            if friendly_spec:
                name_cell: str = str(friendly_spec)
            else:
                name_cell = _friendly_sync_name(
                    proc.get("remote") or "", proc.get("local_path") or ""
                )

            rows.append([
                name_cell,
                _quantity_cell(progress),
                _percentage_cell(progress),
                _last_update_age(progress),
            ])

        content: List[str] = _render_table_lines(headers, rows)

        return CommandResponse(
            title="Rclone Syncs",
            description="",
            content=content,
        )
