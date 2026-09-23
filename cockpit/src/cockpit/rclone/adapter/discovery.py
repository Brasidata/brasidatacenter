import os
import re
import subprocess
import time
from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Union


OPERATIONS: Tuple[str, ...] = (
    "bisync",
    "sync",
    "copy",
    "copyto",
    "move",
    "moveto",
    "mount",
    "serve",
    "rclone",
)

LOG_FLAGS: Tuple[str, ...] = (
    "--log-file",
    "--log-file=",
)

PS_COLUMNS: str = (
    "pid=,etime=,pcpu=,pmem=,ruser=,command="
)

VALUED_FLAGS: Tuple[str, ...] = (
    "--log-file",
    "--config",
    "--filter-from",
    "--files-from",
    "--exclude-from",
    "--include-from",
    "--cache-dir",
    "--temp-dir",
    "--backup-dir",
    "--track-renames-strategy",
    "--drive-server-side-across-configs",
    "--cutoff-mode",
    "--conflict-resolve",
    "--max-delete",
    "--transfers",
    "--checkers",
    "--max-depth",
    "--bwlimit",
    "--tpslimit",
    "--min-size",
    "--max-size",
    "--max-age",
    "--min-age",
    "--retries",
    "--retries-sleep",
    "--low-level-retries",
    "--suffix",
    "--compare-dest",
    "--copy-dest",
    "--bind",
)

STALL_THRESHOLD_SECONDS: int = 300

TERMINAL_ERROR_HINTS: Tuple[str, ...] = (
    "Bisync aborted",
    "Failed to bisync",
    "bisync aborted",
    "Fatal error",
)
TERMINAL_SUCCESS_HINTS: Tuple[str, ...] = (
    "Bisync successful",
    "Elapsed time",
)


SyncSpecValue = Dict[str, Union[str, List[str]]]

SYNC_SPECS: Dict[str, SyncSpecValue] = {
    "root": {
        "name": "root",
        "friendly_name": "Root (My Drive)",
        "remote": "brasidata:",
        "local_path": "/Users/eliasmpjunior/Documents/Brasidata/GDrive/Brasidata/Root",
        "log_file": "/tmp/rclone_bisync_root_REAL.log",
        "stdout_log": "/tmp/rclone-bisync-root.out.log",
        "stderr_log": "/tmp/rclone-bisync-root.err.log",
        "base_flags": [
            "--conflict-resolve", "newer",
            "--max-delete", "-1",
            "--resilient",
            "--no-update-dir-modtime",
        ],
    },
    "shared": {
        "name": "shared",
        "friendly_name": "Shared Brasidata",
        "remote": "brasidata_shared_brasidata:",
        "local_path": "/Users/eliasmpjunior/Documents/Brasidata/GDrive/Brasidata/Brasidata",
        "log_file": "/tmp/rclone_bisync_shared_REAL.log",
        "stdout_log": "/tmp/rclone-bisync-shared.out.log",
        "stderr_log": "/tmp/rclone-bisync-shared.err.log",
        "base_flags": [
            "--conflict-resolve", "newer",
            "--max-delete", "-1",
            "--resilient",
            "--no-update-dir-modtime",
        ],
    },
    "brasibim": {
        "name": "brasibim",
        "friendly_name": "Shared BrasiBIM",
        "remote": "brasidata_shared_brasibim:",
        "local_path": "/Users/eliasmpjunior/Documents/Brasidata/GDrive/Brasidata/BrasiBIM",
        "log_file": "/tmp/rclone_bisync_brasibim_REAL.log",
        "stdout_log": "/tmp/rclone-bisync-brasibim.out.log",
        "stderr_log": "/tmp/rclone-bisync-brasibim.err.log",
        "base_flags": [
            "--conflict-resolve", "newer",
            "--max-delete", "-1",
            "--resilient",
            "--no-update-dir-modtime",
        ],
    },
}

SYNC_GROUP_ALL: List[str] = ["root", "shared", "brasibim"]


def list_sync_names() -> List[str]:
    return list(SYNC_SPECS.keys()) + ["all"]


def resolve_sync_request(name: str) -> List[str]:
    cleaned: str = (name or "").strip().lower()
    if cleaned == "all":
        return list(SYNC_GROUP_ALL)
    if cleaned in SYNC_SPECS:
        return [cleaned]
    return []


def get_sync_spec(name: str) -> Optional[SyncSpecValue]:
    return SYNC_SPECS.get(name)


def build_bisync_argv(
    spec: SyncSpecValue,
    *,
    dry_run: bool = False,
    resync: bool = False,
) -> List[str]:
    local_path: str = str(spec["local_path"])
    remote: str = str(spec["remote"])
    argv: List[str] = [
        "rclone",
        "bisync",
        local_path,
        remote,
    ]
    base_flags_raw: Any = spec.get("base_flags", [])
    base_flags: List[str] = [str(x) for x in (base_flags_raw or [])]
    argv.extend(base_flags)
    log_file: Optional[str] = spec.get("log_file") if isinstance(spec.get("log_file"), str) else None
    if log_file:
        argv.extend(["--log-file", log_file])
    if dry_run:
        argv.append("--dry-run")
    if resync:
        argv.append("--resync")
    return argv


def launch_bisync(
    spec_name: str,
    *,
    dry_run: bool = False,
    resync: bool = False,
) -> Dict[str, Any]:
    spec: Optional[SyncSpecValue] = get_sync_spec(spec_name)
    if spec is None:
        raise KeyError("unknown sync: {}".format(spec_name))

    argv: List[str] = build_bisync_argv(spec, dry_run=dry_run, resync=resync)
    stdout_path: str = str(spec.get("stdout_log") or "/tmp/rclone-bisync-{}.out.log".format(spec_name))
    stderr_path: str = str(spec.get("stderr_log") or "/tmp/rclone-bisync-{}.err.log".format(spec_name))

    parent_env: Dict[str, str] = dict(os.environ)
    brew_bin: str = "/opt/homebrew/bin"
    if brew_bin not in parent_env.get("PATH", ""):
        parent_env["PATH"] = "{}:{}".format(brew_bin, parent_env.get("PATH", ""))

    stdout_fh = open(stdout_path, "ab")
    stderr_fh = open(stderr_path, "ab")
    try:
        process: subprocess.Popen = subprocess.Popen(
            argv,
            executable=_which_rclone(),
            stdout=stdout_fh,
            stderr=stderr_fh,
            env=parent_env,
            preexec_fn=os.setsid,
        )
    except Exception:
        stdout_fh.close()
        stderr_fh.close()
        raise

    return {
        "name": spec_name,
        "friendly_name": spec.get("friendly_name", spec_name),
        "pid": process.pid,
        "command": " ".join(argv),
        "log_file": spec.get("log_file"),
        "stdout_log": stdout_path,
        "stderr_log": stderr_path,
        "dry_run": dry_run,
        "resync": resync,
        "process_ref": process,
    }


def _which_rclone() -> str:
    parent_env: Dict[str, str] = dict(os.environ)
    brew_bin: str = "/opt/homebrew/bin"
    if brew_bin not in parent_env.get("PATH", ""):
        parent_env["PATH"] = "{}:{}".format(brew_bin, parent_env.get("PATH", ""))
    for candidate in ("rclone", "/opt/homebrew/bin/rclone", "/usr/local/bin/rclone"):
        if os.path.isabs(candidate) and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    result: Optional[subprocess.CompletedProcess] = None
    try:
        result = subprocess.run(
            ["command", "-v", "rclone"],
            capture_output=True, text=True, env=parent_env, shell=False,
        )
    except Exception:
        result = None
    if result and result.returncode == 0:
        path_candidate: str = str(result.stdout).strip()
        if path_candidate:
            return path_candidate
    return "rclone"


def discover_sync_logs(
    *,
    only_recent_hours: int = 24,
    include_known_specs: bool = True,
) -> List[Dict[str, Any]]:
    """
    Return "virtual process" descriptors for every configured sync (SYNC_SPECS)
    whose ``log_file`` exists on disk and was modified recently.

    The :func:`discover_rclone_processes` helper only returns rclone binaries
    that are currently alive in the process table.  That is insufficient for
    short-lived bisync runs that exit with an error (``prior lock file``,
    ``Must run --resync to recover``, ...) in less than a second and never
    appear in ``ps`` by the time the user runs ``cockpit rclone --syncs``.

    This helper fills that gap by scanning the configured ``SYNC_SPECS`` log
    files on disk and returning lightweight dicts compatible with the same
    contract expected by :func:`parse_process` and
    :func:`cockpit.rclone.plugin.command.sync._friendly_sync_name`.

    Parameters
    ----------
    only_recent_hours:
        Only return entries whose ``log_file`` mtime is newer than N hours
        in the past.  Defaults to 24 hours so old test runs are not shown.
    include_known_specs:
        If True, iterate over ``SYNC_SPECS``.  Exposed mainly to make the
        helper unit-testable with fake specs.
    """
    found: List[Dict[str, Any]] = []
    now_ts: float = time.time()
    cutoff_seconds: int = max(0, int(only_recent_hours)) * 3600

    specs_iterable: Any = SYNC_SPECS.items() if include_known_specs else []
    name: str
    spec: SyncSpecValue
    for name, spec in specs_iterable:
        log_file_raw: Any = spec.get("log_file")
        if not isinstance(log_file_raw, str) or not log_file_raw:
            continue
        path: str = str(log_file_raw)
        if not os.path.isfile(path):
            continue
        try:
            mtime: float = os.path.getmtime(path)
        except OSError:
            continue
        if cutoff_seconds and (now_ts - mtime) > cutoff_seconds:
            continue
        friendly: Any = spec.get("friendly_name")
        remote: Any = spec.get("remote")
        local_path: Any = spec.get("local_path")
        found.append({
            "pid": None,
            "source": "sync_spec_log_file",
            "spec_name": name,
            "friendly_name": str(friendly) if friendly else name,
            "remote": str(remote) if isinstance(remote, str) else "",
            "local_path": (
                str(local_path) if isinstance(local_path, str) else ""
            ),
            "log_file": path,
            "log_mtime_epoch": mtime,
            "log_mtime_age_seconds": max(0.0, now_ts - mtime),
            "elapsed_seconds": None,
            "cpu_pct": None,
            "mem_pct": None,
            "user": None,
            "command": "configured-sync ({})".format(name),
            "argv": [],
        })

    return found


def discover_rclone_processes() -> List[Dict[str, Any]]:
    cmd: List[str] = ["ps", "-eo", PS_COLUMNS]
    try:
        stdout: str = subprocess.check_output(cmd, text=True)
    except (OSError, subprocess.CalledProcessError):
        return []

    found: List[Dict[str, Any]] = []
    for raw_line in stdout.splitlines():
        line: str = raw_line.strip()
        if not line:
            continue
        parts: List[str] = re.split(r"\s+", line, maxsplit=5)
        if len(parts) < 6:
            continue
        pid_s, elapsed_s, cpu_s, mem_s, user, command = (
            parts[0], parts[1], parts[2], parts[3], parts[4], parts[5],
        )

        argv0: str = command.split()[0] if command else ""
        if os.path.basename(argv0) != "rclone":
            continue

        try:
            pid: int = int(pid_s)
        except ValueError:
            continue
        if pid == os.getpid():
            continue

        elapsed: int = _parse_etime(elapsed_s)
        try:
            cpu_pct: float = float(cpu_s)
        except ValueError:
            cpu_pct = 0.0
        try:
            mem_pct: float = float(mem_s)
        except ValueError:
            mem_pct = 0.0

        found.append({
            "pid": pid,
            "elapsed": elapsed,
            "cpu_pct": cpu_pct,
            "mem_pct": mem_pct,
            "user": user,
            "command": command,
        })
    return found


def parse_process(proc: Dict[str, Any]) -> Dict[str, Any]:
    elapsed_human: str = _format_elapsed(int(proc["elapsed"]))
    tokens: List[str] = proc["command"].split()
    tokens_no_argv0: List[str] = tokens[1:] if tokens else []

    operation: str = _detect_operation(tokens_no_argv0)
    local_path: str
    remote: str
    local_path, remote = _detect_paths(tokens_no_argv0)
    log_file: str = _detect_log_file(tokens_no_argv0)

    return {
        "pid": int(proc["pid"]),
        "user": proc["user"],
        "elapsed": int(proc["elapsed"]),
        "elapsed_human": elapsed_human,
        "cpu_pct": float(proc["cpu_pct"]),
        "mem_pct": float(proc["mem_pct"]),
        "operation": operation,
        "local_path": local_path,
        "remote": remote,
        "log_file": log_file,
        "command": proc["command"],
    }


def read_sync_progress(log_path: str) -> Optional[Dict[str, Any]]:
    if not log_path or not os.path.exists(log_path):
        return None
    try:
        stat = os.stat(log_path)
        log_mtime: float = stat.st_mtime
        size: int = stat.st_size
        chunk_size: int = min(size, 64 * 1024)
        with open(log_path, "rb") as fh:
            if chunk_size > 0:
                fh.seek(size - chunk_size, os.SEEK_SET)
            raw_tail: bytes = fh.read(chunk_size)
        text: str = raw_tail.decode("utf-8", errors="replace")
    except OSError:
        return None

    now: float = time.time()
    now_dt: datetime = datetime.now()

    lines: List[str] = text.splitlines()

    transferred_bytes_done: Optional[str] = None
    transferred_bytes_uom: Optional[str] = None
    transferred_bytes_total: Optional[str] = None
    transferred_bytes_total_uom: Optional[str] = None
    transferred_bytes_pct: Optional[str] = None
    transferred_bytes: Optional[str] = None
    speed: Optional[str] = None
    eta: Optional[str] = None

    transferred_items_done: Optional[str] = None
    transferred_items_total: Optional[str] = None
    transferred_items_pct: Optional[str] = None

    checks_done: Optional[str] = None
    checks_total: Optional[str] = None
    checks_status: Optional[str] = None
    listed: Optional[str] = None
    elapsed_time: Optional[str] = None
    errors: Optional[str] = None

    transferring: List[str] = []
    collecting_transfer: bool = False

    last_bytes_idx: int = -1
    last_items_idx: int = -1

    bytes_pat: re.Pattern[str] = re.compile(
        r"^Transferred:\s*(\d+(?:\.\d+)?)\s+(\S+)\s*/\s*(\d+(?:\.\d+)?)\s+(\S+)\s*,\s*(.*)$"
    )
    items_pat: re.Pattern[str] = re.compile(
        r"^Transferred:\s*(\d+)\s*/\s*(\d+)\s*,\s*(\S+)\s*$"
    )
    checks_pat: re.Pattern[str] = re.compile(
        r"^Checks:\s*(\d+)\s*/\s*(\d+)\s*,\s*(\S+?)(?:,\s*Listed\s+(\d+))?\s*$"
    )
    elapsed_pat: re.Pattern[str] = re.compile(r"^Elapsed time:\s+(.*\S)\s*$")
    errors_pat: re.Pattern[str] = re.compile(r"^Errors:\s+(\d+)\s*$")
    transferring_head_pat: re.Pattern[str] = re.compile(r"^Transferring:\s*$")
    transferring_item_pat: re.Pattern[str] = re.compile(r"^\s*\*\s+(.*\S)\s*$")

    logline_ts_pat: re.Pattern[str] = re.compile(
        r"^(\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})\s+(INFO|NOTICE|ERROR|DEBUG)\s*:\s*(.*)$"
    )

    last_logline_ts: Optional[datetime] = None
    last_error_message: Optional[str] = None
    last_notice_message: Optional[str] = None
    last_info_message: Optional[str] = None

    for idx, line in enumerate(lines):
        stripped: str = line.rstrip()

        m = logline_ts_pat.match(stripped)
        if m:
            try:
                ts_dt: datetime = datetime.strptime(m.group(1), "%Y/%m/%d %H:%M:%S")
                last_logline_ts = ts_dt
            except ValueError:
                ts_dt = None
            level: str = m.group(2)
            msg: str = m.group(3)
            if level == "ERROR":
                last_error_message = msg
            elif level == "NOTICE":
                last_notice_message = msg
            elif level == "INFO":
                last_info_message = msg

        # ---------------- bytes+speed+eta Transferred line
        m = bytes_pat.match(stripped)
        if m:
            last_bytes_idx = idx
            transferred_bytes_done = m.group(1)
            transferred_bytes_uom = m.group(2)
            transferred_bytes_total = m.group(3)
            transferred_bytes_total_uom = m.group(4)
            rest: str = m.group(5).strip()
            rest_parts: List[str] = [p.strip() for p in rest.split(",") if p.strip()]
            if rest_parts:
                transferred_bytes_pct = rest_parts[0]
            if len(rest_parts) >= 2:
                speed = rest_parts[1]
            if len(rest_parts) >= 3 and rest_parts[2].startswith("ETA "):
                eta = rest_parts[2][len("ETA "):].strip()
            transferred_bytes = "{}/{}".format(
                transferred_bytes_done + " " + transferred_bytes_uom,
                transferred_bytes_total + " " + transferred_bytes_total_uom,
            )
            continue

        # ---------------- items Transferred line (pure integers, no UOM)
        m = items_pat.match(stripped)
        if m:
            last_items_idx = idx
            transferred_items_done = m.group(1)
            transferred_items_total = m.group(2)
            transferred_items_pct = m.group(3)
            continue

        m = checks_pat.match(stripped)
        if m:
            checks_done = m.group(1)
            checks_total = m.group(2)
            checks_status = m.group(3)
            listed = m.group(4)
            continue

        m = elapsed_pat.match(stripped)
        if m:
            elapsed_time = m.group(1)
            continue

        m = errors_pat.match(stripped)
        if m:
            errors = m.group(1)
            continue

        if transferring_head_pat.match(stripped):
            collecting_transfer = True
            transferring = []
            continue

        if stripped == "" and collecting_transfer:
            collecting_transfer = False
            continue

        m = transferring_item_pat.match(stripped)
        if m and collecting_transfer:
            transferring.append(m.group(1))
            continue

    def _nearest_ts_before(index: int) -> Optional[datetime]:
        for j in range(index, -1, -1):
            mm = logline_ts_pat.match(lines[j].rstrip())
            if mm:
                try:
                    return datetime.strptime(mm.group(1), "%Y/%m/%d %H:%M:%S")
                except ValueError:
                    return None
        return None

    log_mtime_age_s: float = max(0.0, now - log_mtime)

    last_logline_ts_age_s: Optional[float]
    if last_logline_ts is not None:
        last_logline_ts_age_s = max(0.0, (now_dt - last_logline_ts).total_seconds())
    else:
        last_logline_ts_age_s = None

    last_bytes_ts: Optional[datetime] = _nearest_ts_before(last_bytes_idx) if last_bytes_idx >= 0 else None
    last_items_ts: Optional[datetime] = _nearest_ts_before(last_items_idx) if last_items_idx >= 0 else None

    last_bytes_age_s: Optional[float] = (
        max(0.0, (now_dt - last_bytes_ts).total_seconds()) if last_bytes_ts else None
    )
    last_items_age_s: Optional[float] = (
        max(0.0, (now_dt - last_items_ts).total_seconds()) if last_items_ts else None
    )

    last_progress_age_s: Optional[float] = None
    for candidate in (last_items_age_s, last_bytes_age_s, last_logline_ts_age_s):
        if candidate is not None:
            if last_progress_age_s is None or candidate < last_progress_age_s:
                last_progress_age_s = candidate
    # Fallback final: mtime do arquivo
    if last_progress_age_s is None:
        last_progress_age_s = log_mtime_age_s

    ended_with_error: bool = False
    end_reason: Optional[str] = None
    last_final_message: Optional[str] = last_error_message or last_notice_message or last_info_message
    if last_final_message:
        for hint in TERMINAL_ERROR_HINTS:
            if hint.lower() in last_final_message.lower():
                ended_with_error = True
                end_reason = "error"
                break
        if end_reason is None:
            for hint in TERMINAL_SUCCESS_HINTS:
                if hint.lower() in last_final_message.lower():
                    end_reason = "success_or_normal"
                    break
    else:
        last_final_message = None

    stalled_raw: bool = (
        last_progress_age_s is not None
        and last_progress_age_s > STALL_THRESHOLD_SECONDS
    )
    stall_reason: Optional[str]
    if stalled_raw:
        stall_reason = (
            "no progress update in last {:.0f}s (threshold {:.0f}s)".format(
                last_progress_age_s, STALL_THRESHOLD_SECONDS,
            )
        )
    else:
        stall_reason = None

    status_label: str
    status_reason: Optional[str]
    if end_reason == "success_or_normal":
        status_label = "ENDED OK"
        status_reason = last_final_message
        stalled = False
    elif ended_with_error:
        status_label = "ENDED ERROR"
        status_reason = last_error_message or last_final_message
        stalled = False
    elif stalled_raw:
        status_label = "STALLED"
        status_reason = stall_reason
        stalled = True
    else:
        status_label = "RUNNING"
        status_reason = None
        stalled = False

    return {
        "log_file": log_path,
        "log_file_exists": True,
        "log_size_bytes": size,
        "log_mtime_epoch": log_mtime,
        "log_mtime_age_seconds": log_mtime_age_s,
        "last_logline_timestamp": (
            last_logline_ts.isoformat(sep=" ") if last_logline_ts else None
        ),
        "last_logline_age_seconds": last_logline_ts_age_s,
        "last_progress_bytes_timestamp": (
            last_bytes_ts.isoformat(sep=" ") if last_bytes_ts else None
        ),
        "last_progress_bytes_age_seconds": last_bytes_age_s,
        "last_progress_items_timestamp": (
            last_items_ts.isoformat(sep=" ") if last_items_ts else None
        ),
        "last_progress_items_age_seconds": last_items_age_s,
        "stall_threshold_seconds": STALL_THRESHOLD_SECONDS,
        "stalled": stalled,
        "stall_reason": stall_reason,
        "ended_with_error": ended_with_error,
        "end_reason": end_reason,
        "status_label": status_label,
        "status_reason": status_reason,
        "last_error_message": last_error_message,
        "last_notice_message": last_notice_message,
        "last_info_message": last_info_message,
        "last_final_message": last_final_message,
        "transferred_bytes": transferred_bytes,
        "transferred_bytes_done": transferred_bytes_done,
        "transferred_bytes_uom": transferred_bytes_uom,
        "transferred_bytes_total": transferred_bytes_total,
        "transferred_bytes_total_uom": transferred_bytes_total_uom,
        "transferred_bytes_pct": transferred_bytes_pct,
        "speed": speed,
        "eta": eta,
        "transferred_items_done": transferred_items_done,
        "transferred_items_total": transferred_items_total,
        "transferred_items_pct": transferred_items_pct,
        "checks_done": checks_done,
        "checks_total": checks_total,
        "checks_status": checks_status,
        "listed": listed,
        "elapsed_time_log": elapsed_time,
        "errors": errors,
        "transferring": transferring,
    }


def _parse_etime(raw: str) -> int:
    if not raw:
        return 0
    cleaned: str = raw.strip()
    if not cleaned:
        return 0

    days: int = 0
    hms: str
    if "-" in cleaned:
        days_s, hms = cleaned.split("-", 1)
        try:
            days = int(days_s)
        except ValueError:
            days = 0
    else:
        hms = cleaned

    parts: List[str] = hms.split(":")
    try:
        if len(parts) == 3:
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        elif len(parts) == 2:
            h, m, s = 0, int(parts[0]), int(parts[1])
        elif len(parts) == 1:
            h, m, s = 0, 0, int(parts[0])
        else:
            return days * 86400
    except ValueError:
        return days * 86400

    return days * 86400 + h * 3600 + m * 60 + s


def _format_elapsed(seconds: int) -> str:
    if seconds < 0:
        seconds = 0

    d: int
    rem: int
    d, rem = divmod(seconds, 86400)
    h: int
    rem2: int
    h, rem2 = divmod(rem, 3600)
    m: int
    s: int
    m, s = divmod(rem2, 60)

    if d:
        return "{}d {:02d}h {:02d}m".format(d, h, m)
    if h:
        return "{}h {:02d}m {:02d}s".format(h, m, s)
    if m:
        return "{}m {:02d}s".format(m, s)
    return "{}s".format(s)


def _detect_operation(tokens: List[str]) -> str:
    for token in tokens:
        if token.startswith("-"):
            continue
        if token in OPERATIONS:
            return token
        break
    return "<unknown>"


def _split_equal_flag(token: str) -> Optional[str]:
    if "=" in token:
        left, right = token.split("=", 1)
        return right.strip() or None
    return None


def _flag_value(tokens: List[str], flag_names: Tuple[str, ...]) -> Optional[str]:
    idx: int
    tk: str
    for idx, tk in enumerate(tokens):
        for flag in flag_names:
            if tk == flag:
                if idx + 1 < len(tokens):
                    return tokens[idx + 1]
                return None
            if tk.startswith(flag):
                value: Optional[str] = _split_equal_flag(tk)
                if value is not None:
                    return value
    return None


def _detect_log_file(tokens: List[str]) -> str:
    found: Optional[str] = _flag_value(tokens, LOG_FLAGS)
    return found or ""


def _is_remote_path(token: str) -> bool:
    if ":" not in token:
        return False
    prefix: str = token.split(":", 1)[0]
    if not prefix:
        return False
    if os.sep in prefix or "/" in prefix:
        return False
    return True


def _detect_paths(tokens: List[str]) -> Tuple[str, str]:
    local_candidates: List[str] = []
    remote_candidates: List[str] = []

    seen_op: bool = False
    i: int = 0
    while i < len(tokens):
        tk: str = tokens[i]

        if tk.startswith("-"):
            matched_valued: bool = False
            for vf in VALUED_FLAGS:
                if tk == vf:
                    i += 2
                    matched_valued = True
                    break
                if tk.startswith(vf + "="):
                    i += 1
                    matched_valued = True
                    break
            if matched_valued:
                continue
            i += 1
            continue

        if not seen_op:
            seen_op = True
            i += 1
            continue

        if _is_remote_path(tk):
            remote_candidates.append(tk)
        else:
            local_candidates.append(tk)
        i += 1

    local_path: str = local_candidates[0] if local_candidates else ""
    remote: str = remote_candidates[0] if remote_candidates else ""
    return local_path, remote


def format_age_human(seconds: Optional[Union[int, float]]) -> str:
    if seconds is None:
        return "-"
    try:
        s: float = float(seconds)
    except (TypeError, ValueError):
        return "-"
    if s < 0:
        s = 0.0

    if s < 1:
        return "agora mesmo"
    if s < 60:
        whole: int = int(s)
        return "{}s atrás".format(whole if whole > 0 else 1)

    whole_s: int = int(round(s))
    days: int
    rem: int
    days, rem = divmod(whole_s, 86400)
    hours: int
    rem2: int
    hours, rem2 = divmod(rem, 3600)
    minutes: int
    secs: int
    minutes, secs = divmod(rem2, 60)

    if days:
        if hours:
            return "{}d {}h atrás".format(days, hours)
        return "{}d atrás".format(days)
    if hours:
        return "{}h {:02d}m atrás".format(hours, minutes)
    if secs >= 30:
        minutes += 1
    if minutes == 60:
        return "1h 00m atrás"
    return "{} min atrás".format(minutes)
