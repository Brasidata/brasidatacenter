from typing import Any, ClassVar, Dict, Optional
from importlib import metadata

from ontobdc.cli.plugin.tile.logo import LogoComponent
from ontobdc.shared.domain.port.component import TerminalTileRenderable


class CockpitLogoComponent(LogoComponent):
    """
    Terminal representation of the Cockpit logo.

    Everything about how a logo is drawn — the colouring, the compact marker,
    the large banner, the centering — belongs to OntoBDC's own component and
    is inherited unchanged. Only the brand and the distribution the version
    is read from are Cockpit's.
    """

    PRIMARY_TEXT: ClassVar[str] = "Cock"
    ACCENT_TEXT: ClassVar[str] = "pit"
    TEXT_VALUE: ClassVar[str] = PRIMARY_TEXT + ACCENT_TEXT
    DISTRIBUTION: ClassVar[str] = "cockpit"

    def _version_label(self) -> str:
        version: Optional[str] = self._version
        if version is None:
            version = metadata.version(self.DISTRIBUTION)

        if not version.startswith("v"):
            return f"v{version}"

        return version


class CockpitOperationTile(TerminalTileRenderable):
    """
    The brand tile Cockpit puts in the operation region of the surface.

    The shared renderer draws the top border with a cutout for whichever tile
    the operation region holds, so Cockpit plugs its own brand in there
    instead of drawing a second banner outside the frame.
    """

    def render(
        self,
        *,
        columns: int,
        rows: int,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        return CockpitLogoComponent().render_compact()
