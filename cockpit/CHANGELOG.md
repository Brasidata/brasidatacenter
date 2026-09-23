# Changelog

## Unreleased

### Added

- Initial skeleton package following the InfoBIM/OntoBDC domain distribution pattern.
- `cockpit` console script wired to `cockpit.cli:main` using OntoBDC's command loader (`root_package="cockpit"`).
- Branded CLI presentation surface: `CockpitLogoComponent`, `CockpitOperationTile` and `CockpitTerminalSurfaceAdapter` / `BorderlessCockpitTerminalSurfaceAdapter`.
- `cockpit --version` / `cockpit -v` version command resolved from the installed `cockpit` distribution.
- `cockpit` (bare) and `cockpit --help` / `-h` welcome command rendering a command tree discovered under the `cockpit` package, with `ontobdc` declared as an executable alias.
- `cockpit init` reusing OntoBDC's own `CliInitCommand`.
