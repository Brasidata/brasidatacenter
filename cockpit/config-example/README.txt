OfflineIMAP config example + keyring helpers (macOS Keychain via Python keyring).

Files:
- offlineimap-elias-brasidata.rc  # OfflineIMAP config. NO plaintext secrets — uses oauth2_*_eval.
- offlineimap-elias-brasidata.py  # OfflineIMAP pythonfile helper. Reads/writes keyring entries.

Keyring service name = "offlineimap-elias-brasidata".
Install steps (from cockpit/mail adapter docs):
  pip install offlineimap keyring
  mkdir -p ~/.config/cockpit
  cp offlineimap-elias-brasidata.{rc,py} ~/.config/cockpit/
  chmod 600 ~/.config/cockpit/*
  cockpit mail --auth --client-id=X --client-secret=Y
