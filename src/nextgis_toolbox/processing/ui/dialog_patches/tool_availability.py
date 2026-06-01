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

from functools import partial
from typing import Optional, cast

from qgis.core import Qgis, QgsApplication
from qgis.gui import (
    QgsMessageBar,
    QgsMessageBarItem,
)
from qgis.PyQt.QtCore import QTimer
from qgis.PyQt.QtWidgets import QMenu, QPushButton, QToolButton, QWidget

from nextgis_toolbox.nextgis_toolbox_interface import (
    NextgisToolboxInterface,
)
from nextgis_toolbox.processing.toolbox_algorithm import (
    ToolboxAlgorithm,
)
from nextgis_toolbox.processing.ui.compat import AlgorithmDialog
from nextgis_toolbox.ui.icon import qgis_icon

from .common import AlgorithmDialogPatch
from .dialog_runtime import DialogRuntimeController

MESSAGE_BAR_CLOSE_MENU_OBJECT_NAME = "mCloseMenu"
TOOLBOX_PROVIDER_WARNING_PATCHED_PROPERTY = (
    "_nextgis_toolbox_provider_warning_patched"
)
TOOLBOX_PROVIDER_WARNING_OPEN_SETTINGS_BUTTON_OBJECT_NAME = (
    "_nextgis_toolbox_provider_warning_open_settings_button"
)


class ToolAvailabilityPatch(AlgorithmDialogPatch):
    """Apply tool availability state and provider warning UI."""

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
        """Apply the availability state and provider warning widgets."""
        self._runtime_controller.set_ui_blocked(
            dialog,
            not algorithm.tool.can_run,
        )
        self._apply_provider_warning_patch(dialog, algorithm)

    def _apply_provider_warning_patch(
        self,
        dialog: AlgorithmDialog,
        algorithm: ToolboxAlgorithm,
    ) -> None:
        message_bar = dialog.messageBar()
        if message_bar is None:
            return

        if not message_bar.property(TOOLBOX_PROVIDER_WARNING_PATCHED_PROPERTY):
            message_bar.widgetAdded.connect(
                partial(self._patch_current_provider_warning_item, dialog)
            )
            message_bar.setProperty(
                TOOLBOX_PROVIDER_WARNING_PATCHED_PROPERTY,
                True,
            )

        for item in message_bar.items():
            self._patch_provider_warning_item(dialog, algorithm, item)

    def _patch_current_provider_warning_item(
        self,
        dialog: AlgorithmDialog,
        item: QWidget,
    ) -> None:
        self._patch_provider_warning_item(
            dialog,
            cast(ToolboxAlgorithm, dialog.algorithm()),
            item,
        )

    def _patch_provider_warning_item(
        self,
        dialog: AlgorithmDialog,
        algorithm: ToolboxAlgorithm,
        item: QWidget,
    ) -> None:
        if not isinstance(item, QgsMessageBarItem):
            return

        if not self._is_provider_warning_item(algorithm, item):
            return

        message_bar = dialog.messageBar()
        if message_bar is not None:
            self._hide_close_control(message_bar)

        self._ensure_open_settings_button(dialog, item)

    def _is_provider_warning_item(
        self,
        algorithm: ToolboxAlgorithm,
        item: QgsMessageBarItem,
    ) -> bool:
        if item.level() != Qgis.MessageLevel.Warning:
            return False

        provider = algorithm.provider()
        warning_message = provider.warningMessage()
        if not warning_message:
            return False

        return item.text() == warning_message

    def _ensure_open_settings_button(
        self,
        dialog: AlgorithmDialog,
        item: QgsMessageBarItem,
    ) -> None:
        existing_button = item.findChild(
            QPushButton,
            TOOLBOX_PROVIDER_WARNING_OPEN_SETTINGS_BUTTON_OBJECT_NAME,
        )
        if existing_button is not None:
            return

        button = QPushButton(
            QgsApplication.translate(
                "NGToolboxProcessing",
                "Open settings",
            ),
            item,
        )
        button.setObjectName(
            TOOLBOX_PROVIDER_WARNING_OPEN_SETTINGS_BUTTON_OBJECT_NAME
        )
        button.setIcon(qgis_icon("mActionOptions.svg"))
        button.clicked.connect(lambda: self._open_settings_from_dialog(dialog))
        item.layout().addWidget(button)

    def _open_settings_from_dialog(
        self,
        dialog: AlgorithmDialog,
    ) -> None:
        dialog.close()
        QTimer.singleShot(0, NextgisToolboxInterface.instance().open_settings)

    def _hide_close_control(self, message_bar: QgsMessageBar) -> None:
        close_menu = message_bar.findChild(
            QMenu,
            MESSAGE_BAR_CLOSE_MENU_OBJECT_NAME,
        )
        if close_menu is not None:
            close_menu_parent = close_menu.parent()
            if (
                isinstance(close_menu_parent, QWidget)
                and close_menu_parent is not message_bar
            ):
                close_menu_parent.hide()
                return

        fallback_button: Optional[QToolButton] = None
        for close_button in message_bar.findChildren(QToolButton):
            close_button_parent = close_button.parentWidget()
            if (
                close_button_parent is not None
                and close_button_parent is not message_bar
            ):
                close_button_parent.hide()
                return

            if fallback_button is None:
                fallback_button = close_button

        if fallback_button is not None:
            fallback_button.hide()
