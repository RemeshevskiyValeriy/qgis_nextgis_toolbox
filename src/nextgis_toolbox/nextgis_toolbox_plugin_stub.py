# NextGIS Toolbox Plugin
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

import sys
from typing import TYPE_CHECKING

from osgeo import gdal
from qgis.core import Qgis
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import QT_VERSION_STR, QSysInfo, pyqtSlot

from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.nextgis_toolbox_plugin_interface import (
    NgToolboxPluginInterface,
)
from nextgis_toolbox.notifier.message_bar_notifier import MessageBarNotifier

if TYPE_CHECKING:
    from nextgis_toolbox.notifier.notifier_interface import (
        NotifierInterface,
    )


class NgToolboxPluginStub(NgToolboxPluginInterface):
    """Stub implementation of plugin interface used to notify the user when the plugin failed to start."""

    def __init__(self, iface: QgisInterface) -> None:
        """Initialize the plugin stub."""
        super().__init__(iface)

        logger.debug("<b>✓ Plugin stub created</b>")
        logger.debug(f"<b>ⓘ OS:</b> {QSysInfo().prettyProductName()}")
        logger.debug(f"<b>ⓘ Qt version:</b> {QT_VERSION_STR}")
        logger.debug(f"<b>ⓘ QGIS version:</b> {Qgis.version()}")
        logger.debug(f"<b>ⓘ Python version:</b> {sys.version}")
        logger.debug(f"<b>ⓘ GDAL version:</b> {gdal.__version__}")
        logger.debug(f"<b>ⓘ Plugin version:</b> {self.version}")
        logger.debug(
            f"<b>ⓘ Plugin path:</b> {self.path}"
            + (f" -> {self.path.resolve()}" if self.path.is_symlink() else "")
        )

        self._notifier = None

    @pyqtSlot()
    def open_about_dialog(self) -> None:
        raise NotImplementedError

    @property
    def notifier(self) -> "NotifierInterface":
        """Return the notifier for displaying messages to the user.

        :returns: Notifier interface instance.
        """
        assert self._notifier is not None, "Notifier is not initialized"
        return self._notifier

    def _load_ui(self) -> bool:
        """Load the plugin resources and initialize components."""
        logger.debug("<b>Start stub initialization</b>")

        self._notifier = MessageBarNotifier(self)

        logger.debug("<b>End stub initialization</b>")

        return True

    def _unload_ui(self) -> None:
        """Unload the plugin resources and clean up components."""
        self._notifier.deleteLater()
        self._notifier = None
