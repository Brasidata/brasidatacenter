"""
OfflineIMAP pythonfile helper for elias@brasidata.com account.

This module is imported by OfflineIMAP via the ``pythonfile`` directive in
``~/.config/cockpit/offlineimap-elias-brasidata.rc`` and exposes three
callables that are evaluated by the repository configuration using the
``oauth2_client_id_eval``, ``oauth2_client_secret_eval`` and
``oauth2_refresh_token_eval`` options.

Secrets are stored in the macOS Login Keychain via the ``keyring`` package
that ships with the cockpit virtualenv. No plaintext credentials ever live
inside the ``.rc`` file.
"""

import keyring

from typing import Optional


OFFLINEIMAP_KEYRING_SERVICE: str = "offlineimap-elias-brasidata"
ACCOUNT_CLIENT_ID: str = "oauth2_client_id"
ACCOUNT_CLIENT_SECRET: str = "oauth2_client_secret"
ACCOUNT_REFRESH_TOKEN: str = "oauth2_refresh_token"


def _get_keyring_value(account_name: str) -> Optional[str]:
    value: Optional[str] = keyring.get_password(
        OFFLINEIMAP_KEYRING_SERVICE, account_name
    )
    if value is None:
        return None
    return value.strip() or None


def get_elias_oauth2_client_id() -> Optional[str]:
    return _get_keyring_value(ACCOUNT_CLIENT_ID)


def get_elias_oauth2_client_secret() -> Optional[str]:
    return _get_keyring_value(ACCOUNT_CLIENT_SECRET)


def get_elias_oauth2_refresh_token() -> Optional[str]:
    return _get_keyring_value(ACCOUNT_REFRESH_TOKEN)


def set_elias_oauth2_client_id(value: str) -> None:
    keyring.set_password(
        OFFLINEIMAP_KEYRING_SERVICE, ACCOUNT_CLIENT_ID, (value or "").strip()
    )


def set_elias_oauth2_client_secret(value: str) -> None:
    keyring.set_password(
        OFFLINEIMAP_KEYRING_SERVICE,
        ACCOUNT_CLIENT_SECRET,
        (value or "").strip(),
    )


def set_elias_oauth2_refresh_token(value: str) -> None:
    keyring.set_password(
        OFFLINEIMAP_KEYRING_SERVICE,
        ACCOUNT_REFRESH_TOKEN,
        (value or "").strip(),
    )


def is_elias_oauth2_configured() -> bool:
    return all(
        _get_keyring_value(name) is not None
        for name in (
            ACCOUNT_CLIENT_ID,
            ACCOUNT_CLIENT_SECRET,
            ACCOUNT_REFRESH_TOKEN,
        )
    )
