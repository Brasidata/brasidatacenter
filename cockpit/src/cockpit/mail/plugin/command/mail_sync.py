from typing import Any, ClassVar, Dict, List, Optional, Tuple

from ontobdc.cli.domain.port.command import CliCommandPort
from ontobdc.cli.domain.model.command import CliCommandMetadata
from ontobdc.cli.domain.request.command import CliCommandRequest
from ontobdc.cli.domain.response.command import CommandResponse

from cockpit.mail.adapter.offlineimap_adapter import (
    ACCOUNT_EMAIL_ELIAS,
    CONFIG_RC_PATH,
    LOCAL_MAILDIR_ROOT,
    PYTHONFILE_PATH,
    OfflineimapAdapterError,
    build_authorization_url,
    describe_configuration,
    exchange_authorization_code_for_refresh_token,
    get_oauth_client_id,
    is_oauth_configured,
    run_offlineimap,
    set_oauth_client_id,
    set_oauth_client_secret,
    set_oauth_refresh_token,
)


class MailSyncCommand(CliCommandPort):
    METADATA: CliCommandMetadata = CliCommandMetadata(
        id="mail_sync",
        logical_component="mail",
        description=(
            "Configure, inspect and trigger OfflineIMAP synchronization for "
            "the configured Gmail account.  Supports OAuth2 initial setup "
            "via macOS Keychain, ``--info`` to list remote folders, and "
            "``--sync`` for the actual Maildir download."
        ),
        depends_on=None,
        arguments=[
            {
                "accepts": ["--auth"],
                "description": (
                    "Guided OAuth2 setup for elias@brasidata.com.  Stores "
                    "the client id, client secret and refresh token in the "
                    "macOS Keychain via the pythonfile keyring helper."
                ),
                "usage": "cockpit mail --auth",
            },
            {
                "accepts": ["--info"],
                "description": (
                    "Run OfflineIMAP in ``--info`` mode: connects to Gmail, "
                    "prints the folder list and returns immediately.  Does "
                    "not download any messages."
                ),
                "usage": "cockpit mail --info",
            },
            {
                "accepts": ["--sync"],
                "description": (
                    "Trigger a full OfflineIMAP sync.  Downloads new "
                    "messages into the Maildir at {}.".format(LOCAL_MAILDIR_ROOT)
                ),
                "usage": "cockpit mail --sync",
            },
            {
                "accepts": ["--client-id="],
                "description": (
                    "Optional.  Google OAuth client id.  If not passed with "
                    "``--auth``, the command prints the expected URL and you "
                    "can paste it back when prompted."
                ),
                "usage": "cockpit mail --auth --client-id=X.apps.googleusercontent.com",
            },
            {
                "accepts": ["--client-secret="],
                "description": (
                    "Optional.  Google OAuth client secret to pair with the "
                    "``--client-id`` value above."
                ),
                "usage": "cockpit mail --auth --client-id=X --client-secret=Y",
            },
            {
                "accepts": ["--auth-code="],
                "description": (
                    "Optional.  Authorization code pasted back from the "
                    "OAuth consent screen.  If not provided, the command "
                    "prints the URL and instructions for exchanging it."
                ),
                "usage": "cockpit mail --auth --client-id=X --client-secret=Y --auth-code=4/0AbC...",
            },
        ],
    )

    COMPONENT: ClassVar[str] = "mail"
    FLAG_AUTH: ClassVar[str] = "--auth"
    FLAG_INFO: ClassVar[str] = "--info"
    FLAG_SYNC: ClassVar[str] = "--sync"

    FLAG_CLIENT_ID_PREFIX: ClassVar[str] = "--client-id="
    FLAG_CLIENT_SECRET_PREFIX: ClassVar[str] = "--client-secret="
    FLAG_AUTH_CODE_PREFIX: ClassVar[str] = "--auth-code="

    @staticmethod
    def accepts(args: List[str]) -> bool:
        if not args:
            return False
        return args[0] == MailSyncCommand.COMPONENT

    def __init__(self, request: CliCommandRequest) -> None:
        self._request: CliCommandRequest = request

    def check(self) -> bool:
        return self.__class__.accepts(
            [self.__class__.COMPONENT, *self._request.command_args]
        )

    def run(self) -> CommandResponse:
        args: List[str] = list(self._request.command_args)
        do_auth: bool = self.FLAG_AUTH in args
        do_info: bool = self.FLAG_INFO in args
        do_sync: bool = self.FLAG_SYNC in args

        client_id_arg: Optional[str] = _extract_prefixed(
            args, self.FLAG_CLIENT_ID_PREFIX
        )
        client_secret_arg: Optional[str] = _extract_prefixed(
            args, self.FLAG_CLIENT_SECRET_PREFIX
        )
        auth_code_arg: Optional[str] = _extract_prefixed(
            args, self.FLAG_AUTH_CODE_PREFIX
        )

        if not (do_auth or do_info or do_sync):
            return _render_help(ok=True)

        modes_selected: int = sum([1 for x in (do_auth, do_info, do_sync) if x])
        if modes_selected > 1:
            return _render_help(
                ok=False,
                header="ERROR: Only one of --auth / --info / --sync allowed per invocation.",
            )

        if do_auth:
            return self._run_auth(
                client_id=client_id_arg,
                client_secret=client_secret_arg,
                auth_code=auth_code_arg,
            )

        configured_ok: bool
        try:
            configured_ok = is_oauth_configured()
        except OfflineimapAdapterError as exc:
            return _error_response(
                title="Mail",
                header="Adapter error while reading keychain helpers",
                detail=str(exc),
            )

        if not configured_ok:
            return _error_response(
                title="Mail",
                header="OAuth2 credentials not yet configured.",
                detail=(
                    "Run ``cockpit mail --auth`` first (with --client-id= and "
                    "--client-secret= if you want them pre-filled)."
                ),
                extra_lines=[
                    "",
                    "Credentials are stored in macOS Keychain (service=offlineimap-elias-brasidata).",
                    "Config files: {}".format(CONFIG_RC_PATH),
                    "             {}".format(PYTHONFILE_PATH),
                ],
            )

        mode_label: str = "info" if do_info else "sync"
        try:
            result: Dict[str, Any] = run_offlineimap(mode_label)
        except OfflineimapAdapterError as exc:
            return _error_response(
                title="Mail {}".format(mode_label.upper()),
                header="Failed to start OfflineIMAP.",
                detail=str(exc),
            )

        return _render_run_result(mode_label, result)

    # --- auth flow ---------------------------------------------------------
    def _run_auth(
        self,
        *,
        client_id: Optional[str],
        client_secret: Optional[str],
        auth_code: Optional[str],
    ) -> CommandResponse:
        output: List[str] = []
        output.append("OAuth2 guided setup for {}".format(ACCOUNT_EMAIL_ELIAS))
        output.append("")

        current_client_id: Optional[str] = client_id or get_oauth_client_id()
        final_client_id: Optional[str]
        final_client_secret: Optional[str]
        final_refresh: Optional[str]

        if client_id:
            try:
                set_oauth_client_id(client_id)
                final_client_id = client_id
            except Exception as exc:
                return _error_response(
                    title="Mail AUTH",
                    header="Failed to persist OAuth2 client id into Keychain.",
                    detail=str(exc),
                )
            output.append("OAuth2 client id → saved into macOS Keychain.")
        else:
            final_client_id = current_client_id
            if final_client_id:
                output.append("OAuth2 client id → using pre-existing value from Keychain.")
            else:
                output.append(
                    "OAuth2 client id → MISSING.  Re-run with "
                    "``--client-id=XYZ.apps.googleusercontent.com``."
                )

        if client_secret:
            try:
                set_oauth_client_secret(client_secret)
                final_client_secret = client_secret
                output.append("OAuth2 client secret → saved into macOS Keychain.")
            except Exception as exc:
                return _error_response(
                    title="Mail AUTH",
                    header="Failed to persist OAuth2 client secret into Keychain.",
                    detail=str(exc),
                )
        else:
            try:
                module = _load_helpers_safe()
                final_client_secret = module.get_elias_oauth2_client_secret() if module else None
            except Exception:
                final_client_secret = None
            if final_client_secret:
                output.append("OAuth2 client secret → using pre-existing value from Keychain.")
            else:
                output.append(
                    "OAuth2 client secret → MISSING.  Re-run with "
                    "``--client-secret=<value>``."
                )

        output.append("")
        if final_client_id:
            auth_url: Optional[str] = build_authorization_url(final_client_id)
            output.append("Open the Google OAuth consent screen in your browser:")
            output.append("")
            if auth_url:
                output.append(auth_url)
            output.append("")
            output.append(
                "If your Google Cloud OAuth app is still in Testing mode, make sure "
                "{} is listed as a Test User in the OAuth consent screen.".format(
                    ACCOUNT_EMAIL_ELIAS
                )
            )
            output.append(
                "After accepting the consent screen, copy the authorization code "
                "(``4/0AbC...``) and re-run this command with ``--auth-code=...``."
            )

        if auth_code and final_client_id and final_client_secret:
            try:
                refresh: str = exchange_authorization_code_for_refresh_token(
                    final_client_id, final_client_secret, auth_code
                )
                set_oauth_refresh_token(refresh)
                output.append("")
                output.append(
                    "SUCCESS: Refresh token → saved into macOS Keychain "
                    "(service=offlineimap-elias-brasidata)."
                )
                output.append("")
                output.append("You can now run:")
                output.append("  cockpit mail --info")
                output.append("  cockpit mail --sync")
                return CommandResponse(
                    title="Mail AUTH — SUCCESS",
                    description="",
                    content=output,
                )
            except OfflineimapAdapterError as exc:
                return _error_response(
                    title="Mail AUTH",
                    header="OAuth2 token exchange failed.",
                    detail=str(exc),
                    extra_lines=output,
                )
            except Exception as exc:
                return _error_response(
                    title="Mail AUTH",
                    header="Unexpected error while saving OAuth2 refresh token.",
                    detail=str(exc),
                    extra_lines=output,
                )

        return CommandResponse(
            title="Mail AUTH",
            description="",
            content=output,
        )


def _load_helpers_safe():
    try:
        from cockpit.mail.adapter.offlineimap_adapter import _load_pythonfile_module

        return _load_pythonfile_module()
    except Exception:
        return None


def _extract_prefixed(args: List[str], prefix: str) -> Optional[str]:
    token: str
    for token in args:
        if token.startswith(prefix):
            return token[len(prefix):] or None
    return None


def _render_help(*, ok: bool, header: Optional[str] = None) -> CommandResponse:
    lines: List[str] = []
    if header:
        lines.append(header)
        lines.append("")
    lines.append("Account: {}".format(ACCOUNT_EMAIL_ELIAS))
    lines.append("Maildir: {}".format(LOCAL_MAILDIR_ROOT))
    lines.append("")
    lines.append("Usage:")
    lines.append("  cockpit mail --auth [--client-id=X] [--client-secret=Y] [--auth-code=Z]")
    lines.append("  cockpit mail --info")
    lines.append("  cockpit mail --sync")
    lines.append("")
    lines.append("Available flags (choose one mode):")
    lines.append("  --auth        Guided OAuth2 setup into macOS Keychain.")
    lines.append("  --info        Connect to Gmail IMAP, print folder list (no download).")
    lines.append("  --sync        Run OfflineIMAP; download messages into Maildir.")
    lines.append("")
    lines.append("Credentials stored via keyring in the macOS Login Keychain.")
    lines.append("Config: {}".format(CONFIG_RC_PATH))
    lines.append("Python: {}".format(PYTHONFILE_PATH))
    return CommandResponse(
        title="Mail" if ok else "Mail — ERROR",
        description="",
        content=lines,
    )


def _error_response(
    *,
    title: str,
    header: str,
    detail: str,
    extra_lines: Optional[List[str]] = None,
) -> CommandResponse:
    lines: List[str] = [header, detail, ""]
    if extra_lines:
        lines.extend(extra_lines)
    return CommandResponse(
        title=title,
        description="",
        content=lines,
    )


def _render_run_result(mode: str, result: Dict[str, Any]) -> CommandResponse:
    returncode: Any = result.get("returncode")
    stdout: str = str(result.get("stdout") or "")
    stderr: str = str(result.get("stderr") or "")
    argv: List[Any] = list(result.get("argv") or [])
    timed_out: bool = bool(result.get("timed_out"))

    lines: List[str] = []
    lines.append("Mode: {}".format(mode))
    lines.append("Exit: {}".format("TIMEOUT" if timed_out else returncode))
    lines.append("Account: {}".format(ACCOUNT_EMAIL_ELIAS))
    lines.append("Maildir: {}".format(LOCAL_MAILDIR_ROOT))
    lines.append("")
    lines.append("Command: {}".format(" ".join(str(x) for x in argv)))
    lines.append("")

    if stdout.strip():
        lines.append("--- stdout (last 40 lines) ---")
        tail_stdout: List[str] = stdout.splitlines()[-40:]
        lines.extend(tail_stdout)
        lines.append("")
    if stderr.strip():
        lines.append("--- stderr (last 40 lines) ---")
        tail_stderr: List[str] = stderr.splitlines()[-40:]
        lines.extend(tail_stderr)
        lines.append("")

    ok: bool = (not timed_out) and returncode == 0
    if ok:
        lines.append("Finished successfully.")
        if mode == "sync":
            lines.append(
                "Your local Maildir is now updated.  New files live under "
                "``{}/new`` and indexed messages under ``{}/cur``.".format(
                    LOCAL_MAILDIR_ROOT, LOCAL_MAILDIR_ROOT
                )
            )
    else:
        lines.append(
            "Run finished with issues.  Check stdout/stderr above or run with "
            "``cockpit mail --auth`` first if you see an OAuth2 error."
        )

    title: str = "Mail {} — SUCCESS".format(mode.upper()) if ok else "Mail {} — FAILED".format(mode.upper())
    return CommandResponse(
        title=title,
        description="",
        content=lines,
    )
