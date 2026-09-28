import os
import sys
from functools import partial
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from ontobdc.cli import (
    BORDERLESS_ENVIRONMENT_VARIABLE,
    CliParameterValidationOrchestrator,
)
from ontobdc.cli.adapter.loader import ExceptionCommandResponseLoader
from ontobdc.cli.adapter.logger import (
    InLineLogger,
    NullLogRepository,
    StandardConsoleLogger,
)
from ontobdc.cli.adapter.command import CliCommandRunAdapter
from ontobdc.cli.adapter.argument import CliGlobalArgumentParserAdapter
from ontobdc.cli.adapter.renderer import (
    CommandResponseRenderAdapter,
    ResponseWidgetLoaderAdapter,
)
from ontobdc.shared.adapter.loader import CommandLoader, ParameterLoader
from ontobdc.cli.adapter.suggestion import CommandSuggestionAdapter
from ontobdc.cli.domain.port.logger import LogRepositoryPort, LoggerAwarePort
from ontobdc.cli.domain.model.logger import LogLevel, LogStrategyConfig
from ontobdc.cli.domain.port.command import CliCommandPort
from ontobdc.cli.domain.port.context import CliContextPort
from ontobdc.cli.domain.port.renderer import (
    CommandResponseRendererPort,
    TerminalSurfacePort,
)
from ontobdc.cli.domain.exception.command import CliCommandArgumentException
from ontobdc.cli.domain.response.command import (
    CommandResponse,
    InteractiveCommandResponse,
)
from ontobdc.shared.facade.adapter.logger import ActiveLogRepositoryBroker

from cockpit.cli.adapter.surface import (
    BorderlessCockpitTerminalSurfaceAdapter,
    CockpitTerminalSurfaceAdapter,
)


class CockpitCli:
    """
    The Cockpit command-line shell.

    Dispatch is the same machinery OntoBDC uses for itself: a command is a
    ``CliCommandPort`` discovered under ``cockpit/<domain>/plugin/command``,
    resolved by ``CliCommandRunAdapter``. This only points that machinery at
    the ``cockpit`` package and puts the Cockpit brand on the surface, so a
    new command never needs this file to change.

    Parameter strategies are discovered in both packages, because a Cockpit
    command reuses OntoBDC's own selectors — the container a project is,
    for one — and declares its own alongside them.
    """

    ROOT_PACKAGE: ClassVar[str] = "cockpit"
    EXECUTABLE: ClassVar[str] = "cockpit"
    PARAMETER_ROOT_PACKAGES: ClassVar[Tuple[str, ...]] = ("ontobdc", "cockpit")
    EXECUTABLE_ALIASES: ClassVar[Tuple[str, ...]] = ("ontobdc",)

    RICH_RENDER_TYPE: ClassVar[str] = "rich"
    JSON_RENDER_TYPE: ClassVar[str] = "json"
    HTML_RENDER_TYPE: ClassVar[str] = "html"
    SILENCE_FLAGS: ClassVar[Tuple[str, ...]] = ("--silent", "-s")

    def __init__(self) -> None:
        self._argument_parser: CliGlobalArgumentParserAdapter = (
            CliGlobalArgumentParserAdapter()
        )
        surface: TerminalSurfacePort = (
            BorderlessCockpitTerminalSurfaceAdapter()
            if os.environ.get(BORDERLESS_ENVIRONMENT_VARIABLE) == "1"
            else CockpitTerminalSurfaceAdapter()
        )
        self._renderer: CommandResponseRendererPort = CommandResponseRenderAdapter(
            widget_loader=ResponseWidgetLoaderAdapter(),
            surface=surface,
        )

    def execute(self) -> None:
        """
        Run the command the arguments name and render what it returns.
        """
        render_type: str = self.RICH_RENDER_TYPE
        silent: bool = False
        logger: Optional[LogRepositoryPort] = None
        try:
            incoming_args: List[str] = self._argument_parser.strip_output_flags()
            render_type = self._render_type()
            silent = self._is_silent()
            logger = self._logger_for(render_type)

            resolved_log_level: Optional[LogLevel]
            sanitized_incoming_args: List[str]
            resolved_log_level, sanitized_incoming_args = (
                self._argument_parser.consume_log_level(incoming_args)
            )
            if resolved_log_level is not None:
                _ = LogStrategyConfig(
                    log_level=resolved_log_level,
                    log_repository=logger,
                )

            ActiveLogRepositoryBroker.instance().set(logger)

            command: CliCommandPort = CliCommandRunAdapter.make(
                sanitized_incoming_args,
                logger,
                loader_class=partial(
                    CommandLoader,
                    root_package=self.ROOT_PACKAGE,
                ),
                defer_check=True,
            )

            if command.METADATA.interactive and render_type != self.RICH_RENDER_TYPE:
                raise CliCommandArgumentException(
                    f"Interactive command '{command.METADATA.id}' "
                    f"does not support {render_type} output."
                )

            self._bind_log_level(command, resolved_log_level)

            parameter_validator: CliParameterValidationOrchestrator = (
                CliParameterValidationOrchestrator()
            )
            if parameter_validator.check(
                command,
                sanitized_incoming_args,
                logger,
                ParameterLoader(
                    logger=logger,
                    root_packages=self.PARAMETER_ROOT_PACKAGES,
                ),
            ):
                self._bind_log_strategy(command, logger, resolved_log_level)
                response: CommandResponse = command.run()
                if not silent and not isinstance(
                    response,
                    InteractiveCommandResponse,
                ):
                    self._renderer.render(response, render_type)

                sys.exit(0)

        except SystemExit:
            raise
        except Exception as error:
            response = ExceptionCommandResponseLoader(
                error,
                CommandSuggestionAdapter(
                    executable=self.EXECUTABLE,
                    root_package=self.ROOT_PACKAGE,
                    executable_aliases=self.EXECUTABLE_ALIASES,
                ),
            ).get()
            if not silent:
                self._renderer.render(response, render_type)

            sys.exit(1)
        finally:
            ActiveLogRepositoryBroker.instance().clear()

    def _render_type(self) -> str:
        """
        Return the renderer the invocation asks for.
        """
        if f"--{self.JSON_RENDER_TYPE}" in sys.argv:
            return self.JSON_RENDER_TYPE

        if f"--{self.HTML_RENDER_TYPE}" in sys.argv:
            return self.HTML_RENDER_TYPE

        return self.RICH_RENDER_TYPE

    def _is_silent(self) -> bool:
        """
        Report whether the invocation asks for the response to be suppressed.
        """
        return any(flag in sys.argv for flag in self.SILENCE_FLAGS)

    @staticmethod
    def _logger_for(render_type: str) -> LogRepositoryPort:
        """
        Return the logger that matches the chosen renderer.
        """
        if render_type == CockpitCli.JSON_RENDER_TYPE:
            return NullLogRepository()

        if render_type == CockpitCli.RICH_RENDER_TYPE:
            return InLineLogger()

        return StandardConsoleLogger()

    @staticmethod
    def _bind_log_level(
        command: CliCommandPort,
        log_level: Optional[LogLevel],
    ) -> None:
        """
        Propagate an explicit global log level into the command context.
        """
        if log_level is None:
            return

        request: Optional[Any] = getattr(command, "_request", None)
        context: Optional[CliContextPort] = getattr(request, "context", None)
        if context is None:
            return

        context.set_parameter_value("log_level", log_level)

    @staticmethod
    def _bind_log_strategy(
        command: CliCommandPort,
        logger: LogRepositoryPort,
        log_level: Optional[LogLevel],
    ) -> None:
        """
        Hand a runtime log strategy to a command that declares it takes one.
        """
        if not isinstance(command, LoggerAwarePort):
            return

        log_strategy_kwargs: Dict[str, Any] = {"log_repository": logger}
        if log_level is not None:
            log_strategy_kwargs["log_level"] = log_level

        command.set_log_strategy(LogStrategyConfig(**log_strategy_kwargs))


def main() -> None:
    """
    Entry point of the ``cockpit`` console script.
    """
    CockpitCli().execute()
