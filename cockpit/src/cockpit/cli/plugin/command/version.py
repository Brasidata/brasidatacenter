from typing import ClassVar, List
from importlib.metadata import version as distribution_version

from ontobdc.cli.domain.port.command import CliCommandPort
from ontobdc.cli.domain.model.command import CliCommandMetadata
from ontobdc.cli.domain.request.command import CliCommandRequest
from ontobdc.cli.domain.response.command import CommandResponse


class CockpitVersionCommand(CliCommandPort):
    """
    Command to display the Cockpit package version.

    Cockpit runs on OntoBDC but is a distribution of its own, so the version
    a user asks for here is Cockpit's, not the runtime it sits on.
    """

    METADATA: CliCommandMetadata = CliCommandMetadata(
        id="version",
        logical_component="cli",
        description="Display the version of Cockpit.",
        depends_on=None,
        arguments=[
            {
                "accepts": [
                    "--version",
                    "-v",
                ],
                "description": "Display the Cockpit package version.",
                "usage": "cockpit --version",
            },
        ],
    )

    DISTRIBUTION: ClassVar[str] = "cockpit"
    VERSION_FLAGS: ClassVar[List[str]] = ["--version", "-v"]

    @staticmethod
    def accepts(args: List[str]) -> bool:
        """
        Match the version command at the CLI routing stage.
        """
        return (
            len(args) == 1
            and args[0] in CockpitVersionCommand.VERSION_FLAGS
        )

    def __init__(self, request: CliCommandRequest) -> None:
        self._request: CliCommandRequest = request

    def check(self) -> bool:
        """
        Check if the command is valid.
        Returns True if the command is valid, False otherwise.
        """
        return self.accepts(self._request.command_args)

    def run(self) -> CommandResponse:
        """
        Report the version of the installed Cockpit distribution.
        """
        return CommandResponse(
            title="Cockpit Version",
            description="Display the Cockpit package version.",
            content={
                "version": distribution_version(self.DISTRIBUTION),
            },
        )
