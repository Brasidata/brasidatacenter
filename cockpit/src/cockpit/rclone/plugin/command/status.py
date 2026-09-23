from typing import Any, ClassVar, Dict, List

from ontobdc.cli.domain.port.command import CliCommandPort
from ontobdc.cli.domain.model.command import CliCommandMetadata
from ontobdc.cli.domain.request.command import CliCommandRequest
from ontobdc.cli.domain.response.command import CommandResponse

from cockpit.rclone.adapter.discovery import (
    discover_rclone_processes,
    parse_process,
    read_sync_progress,
)


class RcloneStatusCommand(CliCommandPort):
    """
    Aggregate status overview of all live rclone processes.

    Reports: total processes alive, breakdown by operation type,
    number of processes that declare an explicit ``--log-file``
    (and therefore have a parseable sync snapshot), total distinct
    remotes and local paths touched, plus per-process one-liners.

    No per-file-transferring detail is emitted (that is ``--syncs``).
    """

    METADATA: CliCommandMetadata = CliCommandMetadata(
        id="rclone_status",
        logical_component="rclone",
        description=(
            "Aggregate status of live rclone processes "
            "(count, operation breakdown, logs, remotes)."
        ),
        depends_on=None,
        arguments=[
            {
                "accepts": ["--status"],
                "description": (
                    "Show the aggregate live-rclone status: process count, "
                    "breakdown by operation type, log-file coverage, "
                    "and per-process one-liners."
                ),
                "usage": "cockpit rclone --status",
            },
        ],
    )

    COMPONENT: ClassVar[str] = "rclone"
    FLAG: ClassVar[str] = "--status"

    @staticmethod
    def accepts(args: List[str]) -> bool:
        if not args or args[0] != RcloneStatusCommand.COMPONENT:
            return False
        scoped: List[str] = args[1:]
        if not scoped:
            return False
        return RcloneStatusCommand.FLAG in scoped

    def __init__(self, request: CliCommandRequest) -> None:
        self._request: CliCommandRequest = request

    def check(self) -> bool:
        return self.__class__.accepts(
            [self.__class__.COMPONENT, *self._request.command_args]
        )

    def run(self) -> CommandResponse:
        processes: List[Dict[str, Any]] = [
            parse_process(p) for p in discover_rclone_processes()
        ]

        operation_counts: Dict[str, int] = {}
        remotes: List[str] = []
        local_paths: List[str] = []
        with_log: int = 0
        count_running: int = 0
        count_stalled: int = 0
        count_ended_error: int = 0
        count_ended_ok: int = 0
        count_no_log: int = 0

        for proc in processes:
            op: str = proc["operation"]
            operation_counts[op] = operation_counts.get(op, 0) + 1
            if proc["remote"] and proc["remote"] not in remotes:
                remotes.append(proc["remote"])
            if proc["local_path"] and proc["local_path"] not in local_paths:
                local_paths.append(proc["local_path"])
            if proc["log_file"]:
                with_log += 1

        one_liners: List[Dict[str, Any]] = []
        for proc in processes:
            progress: Dict[str, Any] = (
                read_sync_progress(proc["log_file"]) if proc["log_file"] else {}
            ) or {}

            status_label: str = (
                progress.get("status_label") or ("NO LOG" if not proc["log_file"] else "UNKNOWN")
            )
            stalled: bool = bool(progress.get("stalled"))
            ended_with_error: bool = bool(progress.get("ended_with_error"))
            status_reason: Optional[str] = progress.get("status_reason")
            last_error_message: Optional[str] = progress.get("last_error_message")

            if status_label == "RUNNING":
                count_running += 1
            elif status_label == "STALLED":
                count_stalled += 1
            elif status_label == "ENDED ERROR":
                count_ended_error += 1
            elif status_label == "ENDED OK":
                count_ended_ok += 1
            elif status_label == "NO LOG":
                count_no_log += 1

            snap: str
            if progress.get("transferred_items_done"):
                snap = "items {}/{} ({})".format(
                    progress["transferred_items_done"],
                    progress["transferred_items_total"],
                    progress["transferred_items_pct"] or "?",
                )
                if progress.get("transferred_bytes"):
                    snap += " — {} {} {}".format(
                        progress["transferred_bytes"],
                        progress["speed"] or "",
                        progress["eta"] or "",
                    ).rstrip()
            elif not proc["log_file"]:
                snap = "no log file"
            else:
                snap = "no progress snapshot"

            snap = "{} — {}".format(status_label, snap)
            if status_reason and status_label in ("STALLED", "ENDED ERROR", "ENDED ERROR"):
                reason_short: str = str(status_reason)
                if len(reason_short) > 80:
                    reason_short = reason_short[:77] + "..."
                snap = "{}: {}".format(snap, reason_short)

            one_liners.append({
                "pid": proc["pid"],
                "operation": proc["operation"],
                "remote": proc["remote"],
                "local_path": proc["local_path"],
                "elapsed": proc["elapsed_human"],
                "log_file": proc["log_file"],
                "status_label": status_label,
                "status_reason": status_reason,
                "stalled": stalled,
                "ended_with_error": ended_with_error,
                "last_error_message": last_error_message,
                "snapshot": snap,
            })

        content: Dict[str, Any] = {
            "count": len(processes),
            "operations": operation_counts,
            "remotes": remotes,
            "local_paths": local_paths,
            "with_log_file": with_log,
            "without_log_file": len(processes) - with_log,
            "count_running": count_running,
            "count_stalled": count_stalled,
            "count_ended_error": count_ended_error,
            "count_ended_ok": count_ended_ok,
            "count_no_log": count_no_log,
            "summary_rows": [
                {"values": [
                    str(p["pid"]),
                    p["operation"],
                    p["status_label"],
                    p["remote"],
                    p["local_path"],
                    p["elapsed"],
                    p["snapshot"],
                ]} for p in one_liners
            ],
            "summary_table": {
                "columns": [
                    {"label": "PID", "key": "pid"},
                    {"label": "Op", "key": "operation"},
                    {"label": "Status", "key": "status_label"},
                    {"label": "Remote", "key": "remote"},
                    {"label": "Local path", "key": "local_path"},
                    {"label": "Elapsed", "key": "elapsed"},
                    {"label": "Snapshot", "key": "snapshot"},
                ],
                "rows": [
                    {"values": [
                        str(p["pid"]),
                        p["operation"],
                        p["status_label"],
                        p["remote"],
                        p["local_path"],
                        p["elapsed"],
                        p["snapshot"],
                    ]} for p in one_liners
                ],
            },
            "processes": one_liners,
        }

        title_parts: List[str] = ["Rclone Status"]
        if processes:
            title_parts.append(
                "{} live process".format(len(processes))
                if len(processes) == 1 else "{} live processes".format(len(processes))
            )
        else:
            title_parts.append("0 live processes")
        extra: List[str] = []
        if count_running:
            extra.append("{} running".format(count_running) if count_running != 1 else "1 running")
        if count_stalled:
            extra.append("{} stalled".format(count_stalled) if count_stalled != 1 else "1 stalled")
        if count_ended_error:
            extra.append(
                "{} ended with error".format(count_ended_error)
                if count_ended_error != 1 else "1 ended with error"
            )
        if count_ended_ok:
            extra.append("{} ended ok".format(count_ended_ok) if count_ended_ok != 1 else "1 ended ok")
        if count_no_log:
            extra.append("{} no log".format(count_no_log) if count_no_log != 1 else "1 no log")
        if extra:
            title_parts[-1] = "{} ({})".format(title_parts[-1], ", ".join(extra))
        title: str = " — ".join(title_parts)

        return CommandResponse(
            title=title,
            description=(
                "Aggregate view of rclone processes with automatic "
                "stall/end-of-life detection: operation breakdown, "
                "remotes/paths touched, log-file coverage, and one-line "
                "status + progress snapshot per process."
            ),
            content=content,
        )
