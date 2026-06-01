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

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import QAction, QMenu, QPushButton

from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.processing.toolbox_algorithm import (
    ToolboxAlgorithm,
)
from nextgis_toolbox.processing.ui.compat import AlgorithmDialog
from nextgis_toolbox.ui.icon import plugin_icon

from .common import AlgorithmDialogPatch
from .dialog_runtime import DialogRuntimeController


class AdvancedButtonPatch(AlgorithmDialogPatch):
    """Extend the advanced button menu with browser navigation."""

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
        """Insert the browser action into the advanced menu."""
        advanced_button = self._runtime_controller.advanced_button(dialog)
        if advanced_button is None:
            logger.debug("Advanced button not found in the dialog")
            return

        self._insert_browser_action(advanced_button, algorithm)

    def _insert_browser_action(
        self,
        advanced_button: QPushButton,
        algorithm: ToolboxAlgorithm,
    ) -> None:
        menu = advanced_button.menu()
        if menu is None:
            return

        action_text = QgsApplication.translate(
            "NGToolboxProcessing",
            "Open Tool in Browser",
        )
        if self._find_action_by_text(menu, action_text) is not None:
            return

        open_in_browser_action = QAction(action_text, menu)
        open_in_browser_action.setIcon(plugin_icon())
        open_in_browser_action.triggered.connect(
            lambda: self._open_in_browser(algorithm.tool_web_url())
        )

        first_action = menu.actions()[0] if menu.actions() else None
        if first_action is None:
            menu.addAction(open_in_browser_action)
            return

        menu.insertSeparator(first_action)
        menu.insertAction(first_action, open_in_browser_action)

    def _find_action_by_text(
        self,
        menu: QMenu,
        text: str,
    ) -> Optional[QAction]:
        for action in menu.actions():
            if action.text() == text:
                return action

        return None

    def _open_in_browser(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))
