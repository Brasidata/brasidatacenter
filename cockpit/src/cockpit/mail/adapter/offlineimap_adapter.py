"""
OfflineIMAP adapter for the cockpit ``mail`` component.

This module centralises the paths to the OfflineIMAP configuration and
keyring helpers for ``elias@brasidata.com``, exposes helpers to run the
``--info`` and default sync modes, and provides a small interactive flow
to persist the OAuth2 credentials into the macOS Keychain via ``keyring``.
"""

import importlib.util
import os
import subprocess
import sys
from typing import Any, ClassVar, Dict, List, Optional, Tuple


class OfflineimapAdapterError(RuntimeError):
    pass


ACCOUNT_ALIAS_ELIAS: str = "elias-brasidata"
ACCOUNT_EMAIL_ELIAS: str = "elias@brasidata.com"

VENV_PATH: str = "/Users/eliasmpjunior/Documents/Brasidata/.venv"
PYTHON_BIN: str = os.path.join(VENV_PATH, "bin", "python")
OFFLINEIMAP_BIN: str = os.path.join(VENV_PATH, "bin", "offlineimap")

CONFIG_HOME: str = "/Users/eliasmpjunior/.config/cockpit"
CONFIG_RC_PATH: str = os.path.join(
    CONFIG_HOME, "offlineimap-{}.rc".format(ACCOUNT_ALIAS_ELIAS)
)
PYTHONFILE_PATH: str = os.path.join(
    CONFIG_HOME, "offlineimap-{}.py".format(ACCOUNT_ALIAS_ELIAS)
)

LOCAL_MAILDIR_ROOT: str = (
    "/Users/eliasmpjunior/Documents/Brasidata/E-mail/GMail/Elias"
)

GOOGLE_OAUTH_AUTH_URL: str = (
    "https://accounts.google.com/o/oauth2/v2/auth?"
    "client_id={client_id}"
    "&redirect_uri=urn%3Aietf%3Awg%3Aoauth%3A2.0%3Aoob"
    "&response_type=code"
    "&scope=https%3A%2F%2Fmail.google.com%2F"
    "&access_type=offline"
    "&prompt=consent"
)
GOOGLE_OAUTH_TOKEN_URL: str = "https://oauth2.googleapis.com/token"


def _load_pythonfile_module():
    if not os.path.isfile(PYTHONFILE_PATH):
        raise OfflineimapAdapterError(
            "OfflineIMAP pythonfile helper missing: {}".format(PYTHONFILE_PATH)
        )
    module_name: str = "offlineimap_elias_keyring_helpers"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, PYTHONFILE_PATH)
    if spec is None or spec.loader is None:
        raise OfflineimapAdapterError(
            "Failed to build spec for pythonfile: {}".format(PYTHONFILE_PATH)
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def is_oauth_configured() -> bool:
    module = _load_pythonfile_module()
    return bool(module.is_elias_oauth2_configured())


def set_oauth_client_id(value: str) -> None:
    module = _load_pythonfile_module()
    module.set_elias_oauth2_client_id(value)


def set_oauth_client_secret(value: str) -> None:
    module = _load_pythonfile_module()
    module.set_elias_oauth2_client_secret(value)


def set_oauth_refresh_token(value: str) -> None:
    module = _load_pythonfile_module()
    module.set_elias_oauth2_refresh_token(value)


def get_oauth_client_id() -> Optional[str]:
    module = _load_pythonfile_module()
    return module.get_elias_oauth2_client_id()


def build_authorization_url(client_id: Optional[str]) -> Optional[str]:
    if not client_id:
        return None
    return GOOGLE_OAUTH_AUTH_URL.format(client_id=client_id)


def exchange_authorization_code_for_refresh_token(
    client_id: str,
    client_secret: str,
    authorization_code: str,
) -> str:
    try:
        import urllib.parse as _parse
        import urllib.request as _request
        import json as _json
    except Exception as exc:
        raise OfflineimapAdapterError(
            "Failed to import standard urllib/json libraries: {}".format(str(exc))
        )

    payload: bytes = _parse.urlencode(
        {
            "code": authorization_code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")
    request = _request.Request(GOOGLE_OAUTH_TOKEN_URL, data=payload, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with _request.urlopen(request, timeout=30) as response:
            raw_body: bytes = response.read()
    except Exception as exc:
        raise OfflineimapAdapterError(
            "Failed to exchange authorization code for tokens: {}".format(str(exc))
        )
    try:
        body: Dict[str, Any] = _json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise OfflineimapAdapterError(
            "Google OAuth token endpoint returned non-JSON body: {}".format(str(exc))
        )
    refresh: Any = body.get("refresh_token")
    if not refresh or not isinstance(refresh, str):
        raise OfflineimapAdapterError(
            "OAuth token exchange did not return a refresh_token. "
            "Make sure you used ``prompt=consent`` and the offline scope. "
            "Raw response keys: {}".format(sorted(body.keys()))
        )
    return str(refresh)


def _build_base_argv(mode: str) -> List[str]:
    if not os.path.isfile(CONFIG_RC_PATH):
        raise OfflineimapAdapterError(
            "OfflineIMAP rc file missing: {}".format(CONFIG_RC_PATH)
        )
    if not os.path.isfile(OFFLINEIMAP_BIN):
        raise OfflineimapAdapterError(
            "OfflineIMAP binary not installed in venv: {}".format(OFFLINEIMAP_BIN)
        )
    argv: List[str] = [PYTHON_BIN, OFFLINEIMAP_BIN, "-c", CONFIG_RC_PATH]
    if mode == "info":
        argv.append("--info")
    elif mode not in ("sync",):
        raise OfflineimapAdapterError(
            "Unknown offlineimap mode: {}".format(mode)
        )
    return argv


def run_offlineimap(mode: str) -> Dict[str, Any]:
    argv: List[str] = _build_base_argv(mode)
    env: Dict[str, str] = dict(os.environ)
    brew_bin: str = "/opt/homebrew/bin"
    if brew_bin not in env.get("PATH", ""):
        env["PATH"] = "{}:{}".format(brew_bin, env.get("PATH", ""))

    stdout_lines: List[str] = []
    stderr_lines: List[str] = []
    try:
        process: subprocess.Popen = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=os.path.dirname(CONFIG_RC_PATH),
        )
    except Exception as exc:
        raise OfflineimapAdapterError(
            "Failed to start offlineimap subprocess ({}): {}".format(
                " ".join(argv), str(exc)
            )
        )

    if mode == "info":
        timeout_s: Optional[int] = 90
    else:
        timeout_s = None
    try:
        stdout_raw, stderr_raw = process.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            stdout_raw, stderr_raw = process.communicate()
        except Exception:
            stdout_raw, stderr_raw = b"", b""
        return {
            "mode": mode,
            "argv": argv,
            "returncode": -1,
            "timed_out": True,
            "stdout": stdout_raw.decode("utf-8", errors="replace"),
            "stderr": stderr_raw.decode("utf-8", errors="replace"),
        }

    return {
        "mode": mode,
        "argv": argv,
        "returncode": process.returncode,
        "timed_out": False,
        "stdout": stdout_raw.decode("utf-8", errors="replace"),
        "stderr": stderr_raw.decode("utf-8", errors="replace"),
    }


def describe_configuration() -> Dict[str, Any]:
    return {
        "alias": ACCOUNT_ALIAS_ELIAS,
        "email": ACCOUNT_EMAIL_ELIAS,
        "rc_path": CONFIG_RC_PATH,
        "pythonfile": PYTHONFILE_PATH,
        "offlineimap_bin": OFFLINEIMAP_BIN,
        "venv_python": PYTHON_BIN,
        "local_maildir_root": LOCAL_MAILDIR_ROOT,
    }
