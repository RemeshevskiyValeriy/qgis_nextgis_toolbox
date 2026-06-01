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

from typing import Iterable, Optional

from .advanced_button import AdvancedButtonPatch
from .cancel_button import CancelConfirmationPatch
from .common import AlgorithmDialogPatch
from .demo_button import DemoButtonPatch
from .dialog_runtime import DialogRuntimeController, DialogRuntimePatch
from .help_browser import HelpAnchorClickPatch, HelpImagesPatch
from .help_button import HelpButtonIconPatch
from .message_bar import MessageBarTextColorPatch
from .tool_availability import ToolAvailabilityPatch


class DefaultDialogPatchFactory:
    def __init__(
        self,
        runtime_controller: Optional[DialogRuntimeController] = None,
    ) -> None:
        self._runtime_controller = (
            runtime_controller or DialogRuntimeController()
        )

    def create_runtime_patch(self) -> DialogRuntimePatch:
        return DialogRuntimePatch(self._runtime_controller)

    def create_patches(self) -> Iterable[AlgorithmDialogPatch]:
        return (
            self.create_runtime_patch(),
            MessageBarTextColorPatch(),
            HelpAnchorClickPatch(),
            HelpImagesPatch(),
            HelpButtonIconPatch(self._runtime_controller),
            DemoButtonPatch(runtime_controller=self._runtime_controller),
            AdvancedButtonPatch(self._runtime_controller),
            ToolAvailabilityPatch(self._runtime_controller),
            CancelConfirmationPatch(self._runtime_controller),
        )
