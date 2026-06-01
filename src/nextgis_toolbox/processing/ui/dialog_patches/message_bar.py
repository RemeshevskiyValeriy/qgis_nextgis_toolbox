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

from qgis.core import Qgis
from qgis.gui import (
    QgsMessageBar,
    QgsMessageBarItem,
)
from qgis.PyQt.QtWidgets import QTextBrowser, QWidget

from nextgis_toolbox.processing.toolbox_algorithm import (
    ToolboxAlgorithm,
)
from nextgis_toolbox.processing.ui.compat import AlgorithmDialog

from .common import AlgorithmDialogPatch

MESSAGE_BAR_TEXT_COLOR_PATCHED_PROPERTY = (
    "_nextgis_toolbox_message_bar_text_color_patched"
)


class MessageBarTextColorPatch(AlgorithmDialogPatch):
    def apply(
        self,
        dialog: AlgorithmDialog,
        algorithm: ToolboxAlgorithm,
    ) -> None:
        del algorithm

        message_bar = dialog.messageBar()
        if message_bar is None:
            return

        if not message_bar.property(MESSAGE_BAR_TEXT_COLOR_PATCHED_PROPERTY):
            message_bar.widgetAdded.connect(self._patch_item)
            message_bar.setProperty(
                MESSAGE_BAR_TEXT_COLOR_PATCHED_PROPERTY,
                True,
            )

        self._patch_existing_items(message_bar)

    def _patch_existing_items(self, message_bar: QgsMessageBar) -> None:
        for item in message_bar.items():
            self._patch_item(item)

    def _patch_item(self, item: QWidget) -> None:
        if not isinstance(item, QgsMessageBarItem):
            return

        text_color = self._text_color(item)
        for text_browser in item.findChildren(QTextBrowser):
            text_browser.setStyleSheet(
                self._patched_text_browser_style(
                    text_browser.styleSheet(),
                    text_color,
                )
            )

    def _text_color(self, item: QgsMessageBarItem) -> str:
        if item.level() == Qgis.MessageLevel.Critical:
            return "white"

        return "black"

    def _patched_text_browser_style(
        self,
        current_style: str,
        text_color: str,
    ) -> str:
        text_color_rule = f"QTextEdit, QTextBrowser {{ color: {text_color}; }}"
        if text_color_rule in current_style:
            return current_style

        if not current_style:
            return text_color_rule

        return f"{current_style} {text_color_rule}"
