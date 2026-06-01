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

from typing import TYPE_CHECKING, List, Optional

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QObject, QTimer, pyqtSlot

from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.processing.ui.compat import (
    IS_DESKTOP_PLATFORM,
    AlgorithmDialog,
)

if TYPE_CHECKING:
    from nextgis_toolbox.processing.toolbox_algorithm import (
        ToolboxAlgorithm,
    )

if IS_DESKTOP_PLATFORM or TYPE_CHECKING:
    from nextgis_toolbox.processing.ui.dialog_patcher import (
        AlgorithmDialogPatcher,
    )
else:
    AlgorithmDialogPatcher = object


class AlgorithmDialogManager(QObject):
    """Track created algorithm dialogs and apply UI patches to them."""

    _retry_count = 10

    def __init__(self, parent: Optional[QObject] = None) -> None:
        """Initialize the dialog patch manager."""
        super().__init__(parent)
        self._dialog_patcher = (
            AlgorithmDialogPatcher() if IS_DESKTOP_PLATFORM else None
        )

    @pyqtSlot(object)
    def on_algorithm_instance_created(
        self,
        algorithm: "ToolboxAlgorithm",
    ) -> None:
        """Schedule dialog patching for a newly created algorithm."""
        if self._dialog_patcher is None:
            return

        logger.debug("Algorithm instance created: %s", algorithm.name())
        logger.debug(
            "Scheduling dialog patch for algorithm '%s'",
            algorithm.name(),
        )
        self._schedule_dialog_patch(id(algorithm), self._retry_count)

    def _schedule_dialog_patch(
        self,
        algorithm_object_id: int,
        remaining_attempts: int,
    ) -> None:
        QTimer.singleShot(
            0,
            lambda current_id=algorithm_object_id, attempts=remaining_attempts: (
                self._patch_dialog_with_retry(current_id, attempts)
            ),
        )

    def _patch_dialog_with_retry(
        self,
        algorithm_object_id: int,
        remaining_attempts: int,
    ) -> None:
        if self._patch_dialog(algorithm_object_id):
            return

        if remaining_attempts <= 1:
            logger.debug(
                "Algorithm dialog for algorithm id %s was not found after retries",
                algorithm_object_id,
            )
            return

        self._schedule_dialog_patch(
            algorithm_object_id,
            remaining_attempts - 1,
        )

    def _patch_dialog(self, algorithm_object_id: int) -> bool:
        logger.debug(
            "Searching algorithm dialog for algorithm id %s",
            algorithm_object_id,
        )

        for dialog in self._find_algorithm_dialogs():
            dialog_algorithm = dialog.algorithm()
            if dialog_algorithm is None:
                continue

            if id(dialog_algorithm) != algorithm_object_id:
                continue

            self._dialog_patcher.patch(dialog)
            return True

        return False

    def _find_algorithm_dialogs(self) -> List[AlgorithmDialog]:
        application = QgsApplication.instance()
        if application is None:
            return []

        return [
            widget
            for widget in application.allWidgets()
            if isinstance(widget, AlgorithmDialog)
        ]
