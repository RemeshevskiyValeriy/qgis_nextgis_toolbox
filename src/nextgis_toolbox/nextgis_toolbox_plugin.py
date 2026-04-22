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
from typing import TYPE_CHECKING, Optional

from osgeo import gdal
from qgis.core import Qgis, QgsApplication
from qgis.gui import QgisInterface
from qgis.PyQt.QtCore import (
    QT_VERSION_STR,
    QSysInfo,
    Qt,
    QTimer,
    pyqtSlot,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QMenu
from qgis.utils import iface

from nextgis_toolbox.about_dialog import AboutDialog
from nextgis_toolbox.core.constants import PACKAGE_NAME, PLUGIN_NAME
from nextgis_toolbox.core.exceptions import (
    NgToolboxPluginProcessingRequiredWarning,
)
from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.nextgis_toolbox_plugin_interface import (
    NgToolboxPluginInterface,
)
from nextgis_toolbox.nextgis_toolbox_window import ToolboxDockWidget
from nextgis_toolbox.notifier.message_bar_notifier import MessageBarNotifier

if TYPE_CHECKING:
    from nextgis_toolbox.notifier.notifier_interface import (
        NotifierInterface,
    )

assert isinstance(iface, QgisInterface)


class NgToolboxPlugin(NgToolboxPluginInterface):
    """NextGIS Toolbox Plugin"""

    _notifier: Optional[MessageBarNotifier]

    def __init__(self) -> None:
        super().__init__()

        logger.debug("<b>✓ Plugin created</b>")
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

        self.iface = iface

        self._dock_widget = None
        self._show_action = None
        self._about_action = None
        self._show_help_action = None
        self._plugin_menu = None

        self._first_start = True

        self._notifier = None

    @pyqtSlot()
    def open_about_dialog(self) -> None:
        dialog = AboutDialog(PACKAGE_NAME)
        dialog.exec()

    @property
    def notifier(self) -> "NotifierInterface":
        """Return the notifier for displaying messages to the user.

        :returns: Notifier interface instance.

        :raises AssertionError: If notifier is not initialized.
        """
        assert self._notifier is not None, "Notifier is not initialized"
        return self._notifier

    def _load(self) -> None:
        """Initialize GUI elements."""
        logger.debug("<b>Start plugin initialization</b>")

        self._notifier = MessageBarNotifier(self)

        QTimer.singleShot(0, self._initialize_ui)

    def _initialize_ui(self) -> None:
        """Create plugin UI after QGIS main window is fully initialized."""
        processing_menu = None

        for menu in self.iface.mainWindow().findChildren(QMenu):
            if menu.objectName() == "processing":
                processing_menu = menu
                break

        if processing_menu is None:
            self._notifier.display_exception(
                NgToolboxPluginProcessingRequiredWarning()
            )

            logger.debug(
                "<b>Processing plugin is not enabled. "
                "NextGIS Toolbox Plugin initialization skipped</b>"
            )
            return

        icon_path = self.path / "icons" / "icon.png"

        self._plugin_menu = QMenu(self.iface.mainWindow())
        self._plugin_menu.setTitle("NextGIS Toolbox Plugin")
        self._plugin_menu.setIcon(QIcon(str(icon_path)))

        self._show_action = QAction(
            QIcon(str(icon_path)),
            "NextGIS Toolbox Plugin",
            self.iface.mainWindow(),
        )
        self._show_action.setCheckable(True)
        self._show_action.toggled.connect(self.run)

        self._about_action = QAction(
            QgsApplication.getThemeIcon("mActionPropertiesWidget.svg"),
            self.tr("About plugin…"),
            self.iface.mainWindow(),
        )
        self._about_action.triggered.connect(self.open_about_dialog)

        self._plugin_menu.addAction(self._show_action)
        self._plugin_menu.addAction(self._about_action)

        processing_menu.addMenu(self._plugin_menu)

        attributes_toolbar = self.iface.attributesToolBar()
        if attributes_toolbar is not None:
            attributes_toolbar.addAction(self._show_action)

        self._show_help_action = QAction(
            QIcon(str(icon_path)),
            PLUGIN_NAME,
        )
        self._show_help_action.triggered.connect(self.open_about_dialog)
        plugin_help_menu = self.iface.pluginHelpMenu()
        assert plugin_help_menu is not None
        plugin_help_menu.addAction(self._show_help_action)

        logger.debug("<b>End plugin initialization</b>")

    def _unload(self) -> None:
        """Cleanup plugin UI."""
        logger.debug("<b>Start plugin unloading</b>")

        attributes_toolbar = self.iface.attributesToolBar()
        if attributes_toolbar is not None:
            attributes_toolbar.removeAction(self._show_action)

        if self._plugin_menu is not None:
            for menu in self.iface.mainWindow().findChildren(QMenu):
                if menu.objectName() == "processing":
                    menu.removeAction(self._plugin_menu.menuAction())
                    break

            self._plugin_menu.deleteLater()
            self._plugin_menu = None

        if self._show_action is not None:
            self._show_action.deleteLater()
            self._show_action = None

        if self._about_action is not None:
            self._about_action.deleteLater()
            self._about_action = None

        if self._show_help_action is not None:
            plugin_help_menu = self.iface.pluginHelpMenu()
            assert plugin_help_menu is not None
            plugin_help_menu.removeAction(self._show_help_action)
            self._show_help_action.deleteLater()

        if self._dock_widget:
            self._dock_widget.unload_proc()
            self._dock_widget.close()
            self._dock_widget.deleteLater()
            self._dock_widget = None

        if self._notifier is not None:
            self._notifier.deleteLater()
            self._notifier = None

        logger.debug("<b>End plugin unloading</b>")

    @pyqtSlot(bool)
    def run(self, checked: bool) -> None:
        """Toggle dock widget visibility.

        :param checked: Action state
        """
        if self._first_start and checked:
            self._first_start = False

            try:
                self._dock_widget = ToolboxDockWidget(
                    self.iface,
                    self.iface.mainWindow(),
                )
                self._dock_widget.window_closed.connect(self._on_dock_closed)
            except Exception:
                logger.exception("DockWidget creation failed")
                self._notifier.display_message(
                    self.tr("Failed to initialize NextGIS Toolbox plugin."),
                    level=Qgis.MessageLevel.Critical,
                )
                self._show_action.setChecked(False)
                self._first_start = True
                return

            self.iface.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea,
                self._dock_widget,
            )

            right_docks = [
                dock
                for dock in self.iface.mainWindow().findChildren(QDockWidget)
                if self.iface.mainWindow().dockWidgetArea(dock)
                == Qt.DockWidgetArea.RightDockWidgetArea
            ]

            if right_docks:
                self.iface.mainWindow().tabifyDockWidget(
                    right_docks[0],
                    self._dock_widget,
                )

        if not self._dock_widget:
            return

        self._dock_widget.setVisible(checked)

    @pyqtSlot()
    def _on_dock_closed(self) -> None:
        """Handle dock widget close event."""
        if self._show_action:
            self._show_action.setChecked(False)
