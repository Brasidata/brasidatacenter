"""Convention-based discovery for BrasidataCenter command plugins."""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import pkgutil
from pathlib import Path
from types import ModuleType
from typing import Iterator

from brasidatacenter.cli.domain.command import CommandPort


class CommandDiscoveryError(RuntimeError):
    """Raised when a command package exists but cannot be loaded safely."""


class CommandLoader:
    """Discover commands under ``<component>/plugin/command`` packages."""

    def __init__(
        self,
        logical_component: str,
        root_package: str = "brasidatacenter",
    ) -> None:
        self._logical_component = logical_component
        self._root_package = root_package

    def get(self, command_id: str) -> type[CommandPort] | None:
        """Return the command with the requested metadata identifier."""
        return next(
            (
                command
                for command in self.get_all()
                if command.METADATA.id == command_id
            ),
            None,
        )

    def get_all(self) -> list[type[CommandPort]]:
        """Load every command declared for this loader's component."""
        commands: list[type[CommandPort]] = []

        for package_name in self._command_package_names():
            for module in self._import_modules(package_name):
                for _, candidate in inspect.getmembers(module, inspect.isclass):
                    if not issubclass(candidate, CommandPort) or candidate is CommandPort:
                        continue
                    metadata = getattr(candidate, "METADATA", None)
                    if (
                        getattr(metadata, "logical_component", None)
                        != self._logical_component
                    ):
                        continue
                    if candidate not in commands:
                        commands.append(candidate)

        return commands

    @classmethod
    def logical_components(
        cls,
        root_package: str = "brasidatacenter",
    ) -> list[str]:
        """List components that contain a command plugin directory."""
        components: set[str] = set()
        for root in cls._package_roots(root_package):
            for child in root.iterdir():
                if (
                    child.is_dir()
                    and not child.name.startswith((".", "_"))
                    and (child / "plugin" / "command").is_dir()
                ):
                    components.add(child.name)
        return sorted(components)

    def _command_package_names(self) -> Iterator[str]:
        for component in self.logical_components(self._root_package):
            if component == self._logical_component:
                yield (
                    f"{self._root_package}.{component}.plugin.command"
                )

    @staticmethod
    def _package_roots(root_package: str) -> tuple[Path, ...]:
        try:
            spec = importlib.util.find_spec(root_package)
        except (ImportError, ValueError) as error:
            raise CommandDiscoveryError(
                f"Cannot resolve command root package {root_package!r}."
            ) from error

        if spec is None or not spec.submodule_search_locations:
            raise CommandDiscoveryError(
                f"Cannot resolve command root package {root_package!r}."
            )

        return tuple(Path(location) for location in spec.submodule_search_locations)

    @staticmethod
    def _import_modules(package_name: str) -> Iterator[ModuleType]:
        try:
            command_package = importlib.import_module(package_name)
        except Exception as error:
            raise CommandDiscoveryError(
                f"Cannot import command package {package_name!r}: {error}"
            ) from error

        yield command_package
        package_path = getattr(command_package, "__path__", None)
        if package_path is None:
            return

        prefix = f"{command_package.__name__}."
        for module_info in pkgutil.walk_packages(package_path, prefix):
            try:
                yield importlib.import_module(module_info.name)
            except Exception as error:
                raise CommandDiscoveryError(
                    f"Cannot import command module {module_info.name!r}: {error}"
                ) from error
