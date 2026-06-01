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

from typing import Callable, Optional

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QEvent, QObject, Qt, QTimer
from qgis.PyQt.QtGui import QKeyEvent
from qgis.PyQt.QtWidgets import QAbstractButton, QMessageBox

from nextgis_toolbox.processing.toolbox_algorithm import (
    ToolboxAlgorithm,
)
from nextgis_toolbox.processing.ui.compat import AlgorithmDialog

from .common import AlgorithmDialogPatch
from .dialog_runtime import DialogRuntimeController

STOP_WAITING_DIALOG_TITLE = QgsApplication.translate(
    "NGToolboxProcessing",
    "Stop waiting for the task?",
)
STOP_WAITING_DIALOG_MESSAGE = QgsApplication.translate(
    "NGToolboxProcessing",
    "Stopping the task in QGIS will not stop it on the server. "
    "After completion, the results will still be available in the web interface.\n\n"
    "Do you want to stop waiting for this task?",
)
CANCEL_CONFIRMATION_PATCHED_PROPERTY = (
    "_nextgis_toolbox_cancel_confirmation_patched"
)
CANCEL_CONFIRMATION_BYPASS_PROPERTY = (
    "_nextgis_toolbox_cancel_confirmation_bypass"
)
TOOLBOX_CANCEL_CONFIRMATION_FILTER_ATTRIBUTE = (
    "_nextgis_toolbox_cancel_confirmation_filter"
)


class _CancelConfirmationEventFilter(QObject):
    def __init__(
        self,
        dialog: AlgorithmDialog,
        button: QAbstractButton,
        confirm_cancel: Callable[[], bool],
    ) -> None:
        super().__init__(button)
        self._dialog = dialog
        self._button = button
        self._confirm_cancel = confirm_cancel

    def eventFilter(self, a0: QObject, a1: QEvent) -> bool:
        watched = a0
        event = a1
        if watched is not self._button:
            return False

        if getattr(self._dialog, "feedback", None) is None:
            return False

        if self._button.property(CANCEL_CONFIRMATION_BYPASS_PROPERTY):
            self._button.setProperty(
                CANCEL_CONFIRMATION_BYPASS_PROPERTY,
                False,
            )
            return False

        if not self._button.isEnabled():
            return False

        if event.type() == QEvent.Type.MouseButtonRelease:
            return self._confirm_and_forward()

        if (
            event.type() == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
            and event.key()
            in (
                Qt.Key.Key_Enter,
                Qt.Key.Key_Return,
                Qt.Key.Key_Space,
            )
        ):
            return self._confirm_and_forward()

        return False

    def _confirm_and_forward(self) -> bool:
        if not self._confirm_cancel():
            return True

        self._button.setProperty(CANCEL_CONFIRMATION_BYPASS_PROPERTY, True)
        QTimer.singleShot(0, self._button.click)
        return True


class CancelConfirmationPatch(AlgorithmDialogPatch):
    """Intercept cancel interactions and request explicit confirmation."""

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
        """Attach the cancel confirmation filter to the cancel button."""
        del algorithm

        cancel_button = self._runtime_controller.cancel_button(dialog)
        if not isinstance(cancel_button, QAbstractButton):
            return

        if cancel_button.property(CANCEL_CONFIRMATION_PATCHED_PROPERTY):
            return

        confirmation_filter = _CancelConfirmationEventFilter(
            dialog,
            cancel_button,
            lambda current_dialog=dialog: self._confirm_cancel(current_dialog),
        )
        cancel_button.installEventFilter(confirmation_filter)
        setattr(
            cancel_button,
            TOOLBOX_CANCEL_CONFIRMATION_FILTER_ATTRIBUTE,
            confirmation_filter,
        )
        cancel_button.setProperty(CANCEL_CONFIRMATION_PATCHED_PROPERTY, True)

    def _confirm_cancel(
        self,
        dialog: AlgorithmDialog,
    ) -> bool:
        result = QMessageBox.warning(
            dialog,
            STOP_WAITING_DIALOG_TITLE,
            STOP_WAITING_DIALOG_MESSAGE,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Cancel,
        )
        return result == QMessageBox.StandardButton.Yes
