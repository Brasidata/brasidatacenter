from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union

from ontobdc.cli.domain.port.command import CliCommandPort
from ontobdc.cli.domain.model.command import CliCommandMetadata
from ontobdc.cli.domain.request.command import CliCommandRequest
from ontobdc.cli.domain.response.command import CommandResponse

from cockpit.rclone.adapter.discovery import (
    launch_bisync,
    list_sync_names,
    resolve_sync_request,
)


class RcloneRunCommand(CliCommandPort):
    METADATA: CliCommandMetadata = CliCommandMetadata(
        id="rclone_run",
        logical_component="rclone",
        description=(
            "Trigger a bisync run for one (or all) of the configured sync "
            "mappings by their short name (root / shared / brasibim / all). "
            "Spawns rclone in the background, writing stdout/stderr to the "
            "same log paths used by the launchd plists plus an explicit "
            "--log-file so cockpit rclone --syncs can tail the progress."
        ),
        depends_on=None,
        arguments=[
            {
                "accepts": ["--run"],
                "description": (
                    "Kick off a bisync background run. Takes a short name: "
                    "``cockpit rclone --run root``. Supported names are "
                    "``root``, ``shared``, ``brasibim`` and ``all`` (which "
                    "spawns the three configured mappings in parallel)."
                ),
                "usage": "cockpit rclone --run {root|shared|brasibim|all} [--resync] [--dry-run]",
            },
            {
                "accepts": ["--resync"],
                "description": (
                    "Pass ``--resync`` to rclone bisync. Required once "
                    "after bisync reports ``Must run --resync to recover``."
                ),
                "usage": "cockpit rclone --run root --resync",
            },
            {
                "accepts": ["--dry-run"],
                "description": (
                    "Pass ``--dry-run`` so rclone only reports what it "
                    "would do, without touching any files."
                ),
                "usage": "cockpit rclone --run shared --dry-run",
            },
        ],
    )

    COMPONENT: ClassVar[str] = "rclone"
    FLAG_RUN: ClassVar[str] = "--run"
    FLAG_RUN_EQ: ClassVar[str] = "--run="
    FLAG_RESYNC: ClassVar[str] = "--resync"
    FLAG_DRY_RUN: ClassVar[str] = "--dry-run"

    @staticmethod
    def accepts(args: List[str]) -> bool:
        if not args or args[0] != RcloneRunCommand.COMPONENT:
            return False
        scoped: List[str] = args[1:]
        token: str
        for token in scoped:
            if token == RcloneRunCommand.FLAG_RUN or token.startswith(RcloneRunCommand.FLAG_RUN_EQ):
                return True
        return False

    def __init__(self, request: CliCommandRequest) -> None:
        self._request: CliCommandRequest = request

    def check(self) -> bool:
        return self.__class__.accepts(
            [self.__class__.COMPONENT, *self._request.command_args]
        )

    def run(self) -> CommandResponse:
        args: List[str] = list(self._request.command_args)

        target_name, remaining = _extract_run_value(args)
        dry_run: bool = RcloneRunCommand.FLAG_DRY_RUN in remaining
        resync: bool = RcloneRunCommand.FLAG_RESYNC in remaining

        if target_name is None:
            return _usage_response(
                header="Missing --run value",
                detail="Pass ``cockpit rclone --run <name>``. Valid names: {}.".format(
                    ", ".join(list_sync_names())
                ),
                ok=False,
            )

        names: List[str] = resolve_sync_request(target_name)
        if not names:
            return _usage_response(
                header="Unknown sync name",
                detail="Value ``{}`` is not configured. Valid names: {}.".format(
                    target_name, ", ".join(list_sync_names())
                ),
                ok=False,
            )

        spawned: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        name: str
        for name in names:
            try:
                spawned.append(
                    launch_bisync(
                        name,
                        dry_run=dry_run,
                        resync=resync,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                errors.append({"name": name, "error": str(exc)})

        return _render_result(spawned, errors, dry_run=dry_run, resync=resync)


def _extract_run_value(args: List[str]) -> Tuple[Optional[str], List[str]]:
    remaining: List[str] = []
    value: Optional[str] = None
    i: int = 0
    while i < len(args):
        token: str = args[i]
        if token == RcloneRunCommand.FLAG_RUN:
            if i + 1 < len(args):
                i += 1
                value = args[i]
            else:
                value = ""
        elif token.startswith(RcloneRunCommand.FLAG_RUN_EQ):
            raw_value: str = token[len(RcloneRunCommand.FLAG_RUN_EQ):]
            if raw_value or value is None:
                value = raw_value
        else:
            remaining.append(token)
        i += 1
    return value, remaining


def _usage_response(*, header: str, detail: str, ok: bool) -> CommandResponse:
    lines: List[str] = [
        header,
        detail,
        "",
        "Usage:",
        "  cockpit rclone --run root",
        "  cockpit rclone --run shared --resync",
        "  cockpit rclone --run brasibim --dry-run",
        "  cockpit rclone --run all",
    ]
    return CommandResponse(
        title="Rclone Run" if ok else "Rclone Run — ERROR",
        description="",
        content=lines,
    )


def _render_result(
    spawned: List[Dict[str, Any]],
    errors: List[Dict[str, Any]],
    *,
    dry_run: bool,
    resync: bool,
) -> CommandResponse:
    headers: List[str] = [
        "Sync",
        "Status",
        "PID",
        "Flags",
        "Log (--syncs)",
    ]
    rows: List[List[str]] = []

    item: Dict[str, Any]
    for item in spawned:
        flags_list: List[str] = []
        if bool(item.get("dry_run")):
            flags_list.append("dry-run")
        if bool(item.get("resync")):
            flags_list.append("resync")
        flags: str = ",".join(flags_list) if flags_list else "-"
        log_value: Any = item.get("log_file")
        rows.append([
            str(item.get("friendly_name", item.get("name", "?"))),
            "SPAWNED",
            str(item.get("pid", "?")),
            flags,
            str(log_value) if log_value else "-",
        ])

    err: Dict[str, Any]
    for err in errors:
        rows.append([
            str(err.get("name", "?")),
            "ERROR: {}".format(str(err.get("error", "?"))),
            "-",
            "-",
            "-",
        ])

    summary_lines: List[str] = [""]
    ok_total: int = len(spawned)
    err_total: int = len(errors)

    if ok_total:
        spawned_names: List[str] = [
            "{}={}".format(str(x.get("name", "?")), str(x.get("pid", "?")))
            for x in spawned
        ]
        summary_lines.append("Launched {} process(es): {}.".format(ok_total, ", ".join(spawned_names)))
    if err_total:
        summary_lines.append("{} launch(es) failed. Check stderr log above for details.".format(err_total))

    if dry_run or resync:
        mode_bits: List[str] = []
        if dry_run:
            mode_bits.append("--dry-run")
        if resync:
            mode_bits.append("--resync")
        summary_lines.append("Mode: {}.".format(" + ".join(mode_bits)))
    summary_lines.append("Follow progress with: cockpit rclone --syncs")
    summary_lines.append("")

    table_lines: List[str] = _render_plain_rows(headers, rows)
    content: List[str] = table_lines + summary_lines

    title: str = "Rclone Run"
    if err_total and not ok_total:
        title = "Rclone Run — ALL FAILED"
    elif err_total:
        title = "Rclone Run — {} FAILED".format(err_total)

    return CommandResponse(
        title=title,
        description="",
        content=content,
    )


def _render_plain_rows(headers: List[str], rows: List[List[str]]) -> List[str]:
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

    lines.append("")
    return lines
