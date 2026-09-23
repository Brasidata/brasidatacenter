from typing import ClassVar, List, Tuple

from ontobdc.cli.adapter.tree import CommandTreeAdapter
from ontobdc.cli.adapter.logger import NullLogRepository
from ontobdc.cli.domain.port.logger import LogRepositoryPort
from ontobdc.cli.domain.port.command import CliCommandPort
from ontobdc.cli.domain.model.command import CliCommandMetadata
from ontobdc.cli.domain.request.command import CliCommandRequest
from ontobdc.cli.domain.response.command import HelpCommandResponse


class CockpitWelcomeCommand(CliCommandPort):
    """
    Command shown by ``cockpit`` with no arguments.

    The tree it renders is Cockpit's own: the discovery walks the ``cockpit``
    package, so what a user sees listed is what this executable answers to,
    not what the runtime underneath happens to carry.
    """

    METADATA: CliCommandMetadata = CliCommandMetadata(
        id="welcome",
        logical_component="cli",
        description="Display the Cockpit commands and options.",
        depends_on=None,
        arguments=[
            {
                "accepts": [
                    "--help",
                    "-h",
                ],
                "description": "Display the command tree.",
            },
        ],
    )

    ROOT_PACKAGE: ClassVar[str] = "cockpit"
    EXECUTABLE: ClassVar[str] = "cockpit"
    EXCLUDED_COMMAND_IDS: ClassVar[Tuple[str, ...]] = ("welcome",)
    EXECUTABLE_ALIASES: ClassVar[Tuple[str, ...]] = ("ontobdc",)

    @staticmethod
    def accepts(args: List[str]) -> bool:
        """
        Match the bare executable, or an explicit request for the tree.
        """
        if not args:
            return True

        return len(args) == 1 and args[0] in ["--help", "-h"]

    def __init__(self, request: CliCommandRequest) -> None:
        self._request: CliCommandRequest = request

    def check(self) -> bool:
        """
        Check if the command is valid.
        Returns True if the command is valid, False otherwise.
        """
        return self.__class__.accepts(self._request.command_args)

    def run(self) -> HelpCommandResponse:
        """
        List the commands this executable answers to.
        """
        logger: LogRepositoryPort = NullLogRepository()
        command_tree: str = CommandTreeAdapter(
            logger=logger,
            root_package=self.ROOT_PACKAGE,
            executable=self.EXECUTABLE,
            excluded_command_ids=self.EXCLUDED_COMMAND_IDS,
            executable_aliases=self.EXECUTABLE_ALIASES,
        ).render()

        return HelpCommandResponse(
            title="Cockpit Commands",
            description="Available commands and options.",
            content={
                "Usage": f"{self.EXECUTABLE} <command> [flags/parameters]",
                "Commands": command_tree,
            },
        )
