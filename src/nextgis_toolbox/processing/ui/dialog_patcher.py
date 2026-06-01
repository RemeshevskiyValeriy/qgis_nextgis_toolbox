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

from typing import Optional, Sequence, cast

from nextgis_toolbox.core.utils import PluginRuntimeProfiler
from nextgis_toolbox.processing.toolbox_algorithm import (
    ToolboxAlgorithm,
)
from nextgis_toolbox.processing.ui.compat import AlgorithmDialog

from .dialog_patches.common import AlgorithmDialogPatch
from .dialog_patches.dialog_runtime import DialogRuntimePatch
from .dialog_patches.patch_factory import DefaultDialogPatchFactory


class AlgorithmDialogPatcher:
    def __init__(
        self,
        patches: Optional[Sequence[AlgorithmDialogPatch]] = None,
        patch_factory: Optional[DefaultDialogPatchFactory] = None,
    ) -> None:
        self._patch_factory = patch_factory or DefaultDialogPatchFactory()
        configured_patches = list(
            patches or self._patch_factory.create_patches()
        )
        if not any(
            isinstance(patch, DialogRuntimePatch)
            for patch in configured_patches
        ):
            configured_patches.insert(
                0,
                self._patch_factory.create_runtime_patch(),
            )

        self._patches = configured_patches

    @PluginRuntimeProfiler.wrap(
        "patching algorithm '{}' dialog",
        format_args=lambda dialog: dialog.algorithm().name(),
    )
    def patch(self, dialog: AlgorithmDialog) -> None:
        algorithm = cast(ToolboxAlgorithm, dialog.algorithm())

        for patch in self._patches:
            patch.apply(dialog, algorithm)

        dialog.updateRunButtonVisibility()
