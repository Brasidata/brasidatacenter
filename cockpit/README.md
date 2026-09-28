# Cockpit

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

> **If you just landed**: Cockpit is an **OntoBDC domain application**, built on
> top of the generic OntoBDC semantic runtime — install the sibling `ontobdc/`
> package first, then this one.
>
> Cockpit sits on the same architecture as `infobim` and any other domain
> subrepo in the OntoBDC stack: a `cockpit` console script dispatches to
> `CliCommandPort` classes discovered under `src/cockpit/<domain>/plugin/command/`.
> Everything above is declared, not hardcoded — add a new command module and
> the loader picks it up with no changes to `cockpit.cli`.

---

## 3-minute Quickstart

```bash
# 1. Prerequisites: ontobdc installed in the same environment
#    (run the sibling ontobdc/reinstall.sh if needed)

# 2. Install cockpit in editable mode
./reinstall.sh

# 3. Initialize a shared workspace
mkdir -p ~/cockpit-workspace && cd ~/cockpit-workspace
cockpit init

# 4. Confirm the CLI is alive
cockpit --version
cockpit
```

---

## Layout

```text
cockpit/ (this package)
├── src/
│   └── cockpit/               # distribution package discovered by the CLI loader
│       ├── cli/
│       │   ├── __init__.py    # CockpitCli entry point -> cockpit.cli:main
│       │   ├── adapter/
│       │   │   ├── logo.py    # Cockpit brand tile / logo
│       │   │   └── surface.py # terminal surface using the Cockpit brand
│       │   └── plugin/
│       │       └── command/
│       │           ├── init.py       # re-export of ontobdc's CliInitCommand
│       │           ├── version.py    # cockpit --version
│       │           └── welcome.py    # bare `cockpit` and `cockpit --help`
│       └── __init__.py       # empty, purely a package marker
├── CHANGELOG.md
├── LICENSE
├── README.md
├── pyproject.toml            # name=cockpit, console_script cockpit=cockpit.cli:main
└── reinstall.sh
```

To add a new domain command, mirror the layout used by `src/cockpit/cli/` under
a new sibling subpackage (e.g. `src/cockpit/workspace/plugin/command/...`).

---

## License

[Apache License 2.0](LICENSE).
