# NextGIS Toolbox
# Copyright (C) 2026  NextGIS
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or any
# later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, see <https://www.gnu.org/licenses/>.


from typing import Optional

from nextgis_toolbox.processing.toolbox_algorithm import (
    ToolboxAlgorithm,
)
from nextgis_toolbox.processing.ui.compat import AlgorithmDialog
from nextgis_toolbox.processing.ui.dialog_patches.common import (
    AlgorithmDialogPatch,
)
from nextgis_toolbox.processing.ui.dialog_patches.dialog_runtime import (
    DialogRuntimeController,
)
from nextgis_toolbox.ui.icon import plugin_icon


class HelpButtonIconPatch(AlgorithmDialogPatch):
    """Apply the plugin icon to the dialog help button."""

    def __init__(
        self,
        runtime_controller: Optional[DialogRuntimeController] = None,
    ) -> None:
        self._runtime_controller = (
            runtime_controller or DialogRuntimeController()
        )

    def apply(
        self,
        dialog: AlgorithmDialog,
        algorithm: ToolboxAlgorithm,
    ) -> None:
        """Set the branded icon on the help button."""
        del algorithm

        help_button = self._runtime_controller.help_button(dialog)
        if help_button is None:
            return

        help_button.setIcon(plugin_icon("nextgis_logo.svg"))
