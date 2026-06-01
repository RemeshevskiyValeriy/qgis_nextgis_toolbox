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

from nextgis_toolbox.processing.ui.dialog_patches.advanced_button import (
    AdvancedButtonPatch,
)
from nextgis_toolbox.processing.ui.dialog_patches.cancel_button import (
    CancelConfirmationPatch,
)
from nextgis_toolbox.processing.ui.dialog_patches.common import (
    AlgorithmDialogPatch,
)
from nextgis_toolbox.processing.ui.dialog_patches.demo_button import (
    DemoButtonPatch,
)
from nextgis_toolbox.processing.ui.dialog_patches.dialog_runtime import (
    DialogRuntimePatch,
)
from nextgis_toolbox.processing.ui.dialog_patches.help_browser import (
    HelpAnchorClickPatch,
    HelpImagesPatch,
)
from nextgis_toolbox.processing.ui.dialog_patches.help_button import (
    HelpButtonIconPatch,
)
from nextgis_toolbox.processing.ui.dialog_patches.message_bar import (
    MessageBarTextColorPatch,
)
from nextgis_toolbox.processing.ui.dialog_patches.tool_availability import (
    ToolAvailabilityPatch,
)

__all__ = [
    "AdvancedButtonPatch",
    "AlgorithmDialogPatch",
    "CancelConfirmationPatch",
    "DemoButtonPatch",
    "DialogRuntimePatch",
    "HelpAnchorClickPatch",
    "HelpButtonIconPatch",
    "HelpImagesPatch",
    "MessageBarTextColorPatch",
    "ToolAvailabilityPatch",
]
