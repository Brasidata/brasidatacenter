from typing import Any, ClassVar, Dict, List

from ontobdc.cli.domain.port.command import CliCommandPort
from ontobdc.cli.domain.model.command import CliCommandMetadata
from ontobdc.cli.domain.request.command import CliCommandRequest
from ontobdc.cli.domain.response.command import CommandResponse

from cockpit.rclone.adapter.discovery import (
    discover_rclone_processes,
    parse_process,
)


class RcloneListCommand(CliCommandPort):
    """
    List all rclone processes currently alive on the host with their
    static process metadata (PID, user, CPU/memory %, operation,
    local path, remote, log file, elapsed time from ``ps``).

    No log files are read: this is a pure process listing.
    """

    METADATA: CliCommandMetadata = CliCommandMetadata(
        id="rclone_list",
        logical_component="rclone",
        description=(
            "List active rclone processes with runtime metadata "
            "(PID, user, CPU/memory, operation, paths, log file)."
        ),
        depends_on=None,
        arguments=[
            {
                "accepts": ["--list"],
                "description": (
                    "List every live rclone process with its process-level "
                    "metadata (PID, user, CPU%, MEM%, operation, local path, "
                    "remote, log file)."
                ),
                "usage": "cockpit rclone --list",
            },
        ],
    )

    COMPONENT: ClassVar[str] = "rclone"
    FLAG: ClassVar[str] = "--list"

    @staticmethod
    def accepts(args: List[str]) -> bool:
        if not args or args[0] != RcloneListCommand.COMPONENT:
            return False
        scoped: List[str] = args[1:]
        if not scoped:
            return False
        return RcloneListCommand.FLAG in scoped

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

        rows: List[Dict[str, Any]] = []
        for proc in processes:
            rows.append({
                "values": [
                    str(proc["pid"]),
                    proc["user"],
                    proc["elapsed_human"],
                    "{:.1f}".format(proc["cpu_pct"]),
                    "{:.1f}".format(proc["mem_pct"]),
                    proc["operation"],
                    proc["local_path"],
                    proc["remote"],
                    proc["log_file"],
                ]
            })

        content: Dict[str, Any] = {
            "count": len(processes),
            "table": {
                "columns": [
                    {"label": "PID", "key": "pid"},
                    {"label": "User", "key": "user"},
                    {"label": "Elapsed", "key": "elapsed"},
                    {"label": "CPU %", "key": "cpu_pct"},
                    {"label": "MEM %", "key": "mem_pct"},
                    {"label": "Operation", "key": "operation"},
                    {"label": "Local path", "key": "local_path"},
                    {"label": "Remote", "key": "remote"},
                    {"label": "Log file", "key": "log_file"},
                ],
                "rows": rows,
            },
            "processes": processes,
        }

        title: str = "Rclone Process List — {} process".format(len(processes))
        if len(processes) != 1:
            title += "es"

        return CommandResponse(
            title=title,
            description=(
                "Every live rclone process on the host, with runtime "
                "metadata from the process table (no log files read)."
            ),
            content=content,
        )
