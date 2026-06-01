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

from math import ceil
from typing import TYPE_CHECKING, Optional

from qgis.core import Qgis
from qgis.PyQt.QtCore import QObject, QTimer, pyqtSlot

from nextgis_toolbox.nextgis_toolbox.tools.models import ToolsManagerState
from nextgis_toolbox.notifier.message_bar_notifier import MessageBarNotifier

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

    from nextgis_toolbox.nextgis_toolbox.tools.tools_interface import (
        ToolsInterface,
    )
    from nextgis_toolbox.notifier.notifier_interface import (
        NotifierInterface,
    )

from nextgis_toolbox.processing.ui.compat import IS_DESKTOP_PLATFORM

if TYPE_CHECKING or IS_DESKTOP_PLATFORM:
    from qgis.PyQt.QtWidgets import QProgressBar
else:
    QProgressBar = object


class CatalogRefreshProgressManager(QObject):
    """Display GUI progress for toolbox catalog loading."""

    def __init__(
        self,
        qgis_iface: "QgisInterface",
        notifier: "NotifierInterface",
        parent: Optional[QObject] = None,
    ) -> None:
        """Initialize the catalog progress manager."""
        super().__init__(parent)
        self._qgis_iface = qgis_iface
        self._notifier = notifier
        self._catalog_progress_message_id = None
        self._catalog_progress_bar = None
        self._catalog_progress_generation = 0
        self._catalog_progress_value = 0.0
        self._delay_next_refresh_feedback = True
        self._show_catalog_progress_immediately = False
        self._tools_state = ToolsManagerState.INITIALIZATION

    def connect_tools_manager(
        self,
        tools_manager: "ToolsInterface",
    ) -> None:
        """Bind toolbox manager signals to GUI-specific slots."""
        tools_manager.loading_progress_changed.connect(
            self.on_catalog_load_progress_changed
        )
        tools_manager.state_changed.connect(self.on_runtime_state_changed)

    @pyqtSlot()
    def reset_refresh_feedback_delay(self) -> None:
        """Delay the progress popup for the next catalog refresh."""
        self._delay_next_refresh_feedback = True

    @pyqtSlot(float)
    def on_catalog_load_progress_changed(self, progress: float) -> None:
        self._catalog_progress_value = self._clamp_progress_value(progress)

        if self._catalog_progress_bar is None:
            return

        self._catalog_progress_bar.setValue(
            self._normalize_progress_value(self._catalog_progress_value)
        )

    @pyqtSlot(object)
    def on_runtime_state_changed(
        self,
        state: ToolsManagerState,
    ) -> None:
        self._tools_state = state

        if state == ToolsManagerState.LOADING:
            self._catalog_progress_value = 0
            self._show_catalog_progress_immediately = (
                not self._delay_next_refresh_feedback
            )
            self._delay_next_refresh_feedback = False
            self._schedule_catalog_progress_message()
            return

        self._catalog_progress_generation += 1
        self._show_catalog_progress_immediately = False
        self._dismiss_catalog_progress_message()

    def _clamp_progress_value(self, progress: float) -> float:
        return max(0.0, min(100.0, progress))

    def _normalize_progress_value(self, progress: float) -> int:
        return ceil(self._clamp_progress_value(progress))

    def _schedule_catalog_progress_message(self) -> None:
        generation = self._catalog_progress_generation + 1
        self._catalog_progress_generation = generation
        if self._show_catalog_progress_immediately:
            self._show_catalog_progress_immediately = False
            self._show_catalog_progress_message(generation)
            return

        self._show_catalog_progress_immediately = False
        QTimer.singleShot(
            3000,
            lambda current_generation=generation: (
                self._show_catalog_progress_message(current_generation)
            ),
        )

    def _show_catalog_progress_message(
        self,
        generation: int,
    ) -> None:
        if generation != self._catalog_progress_generation:
            return

        if self._tools_state != ToolsManagerState.LOADING:
            return

        if (
            self._catalog_progress_bar is not None
            or self._catalog_progress_message_id is not None
        ):
            return

        if not isinstance(self._notifier, MessageBarNotifier):
            return

        progress_bar = QProgressBar(self._qgis_iface.mainWindow())
        progress_bar.setRange(0, 100)
        progress_bar.setValue(
            self._normalize_progress_value(self._catalog_progress_value)
        )
        progress_bar.setTextVisible(False)
        progress_bar.setFixedWidth(140)
        progress_bar.setFixedHeight(12)
        progress_bar.setStyleSheet(
            "QProgressBar::chunk { width: 1px; margin: 0px; }"
        )
        progress_bar.destroyed.connect(
            lambda *_args, current_bar=progress_bar: (
                self._on_progress_bar_destroyed(current_bar)
            )
        )
        self._catalog_progress_bar = progress_bar
        self._catalog_progress_message_id = self._notifier.display_message(
            self.tr("Refreshing tools list…"),
            level=Qgis.MessageLevel.Info,
            widgets=[progress_bar],
            duration=0,
        )
        progress_bar.setValue(
            self._normalize_progress_value(self._catalog_progress_value)
        )

    def _dismiss_catalog_progress_message(self) -> None:
        message_id = self._catalog_progress_message_id
        if message_id is not None and isinstance(
            self._notifier, MessageBarNotifier
        ):
            self._notifier.dismiss_message(message_id)

        self._clear_catalog_progress_message_state()

    def _on_progress_bar_destroyed(
        self,
        progress_bar: Optional[QObject],
    ) -> None:
        if self._catalog_progress_bar is not progress_bar:
            return

        self._clear_catalog_progress_message_state()

    def _clear_catalog_progress_message_state(self) -> None:
        self._catalog_progress_message_id = None
        self._catalog_progress_bar = None
