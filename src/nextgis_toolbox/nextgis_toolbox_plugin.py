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
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from osgeo import gdal
from processing import execAlgorithmDialog
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
from nextgis_toolbox.nextgis_toolbox.api.toolbox import Toolbox
from nextgis_toolbox.nextgis_toolbox_plugin_interface import (
    NgToolboxPluginInterface,
)
from nextgis_toolbox.nextgis_toolbox_window import ToolboxDockWidget
from nextgis_toolbox.notifier.message_bar_notifier import MessageBarNotifier
from nextgis_toolbox.processing.nextgis_toolbox_plugin_provider import (
    NgToolboxPluginProcessingProvider,
)
from nextgis_toolbox.settings.nextgis_toolbox_plugin_settings_page import (
    NgToolboxPluginSettingsPageFactory,
)
from nextgis_toolbox.ui.icon import material_icon, plugin_icon, qgis_icon

if TYPE_CHECKING:
    from nextgis_toolbox.notifier.notifier_interface import (
        NotifierInterface,
    )

assert isinstance(iface, QgisInterface)

_QGIS_ICON = "qgis"
_PLUGIN_ICON = "plugin"
_MATERIAL_ICON = "material"

# Mapping: tag_id (stable, language-independent) → (icon_source, icon_name)
# Tag IDs do not change when the API returns responses in different languages.

# fmt: off
_CATEGORY_ICON_MAP: Dict[int, Tuple[str, str]] = {
    1: (_MATERIAL_ICON, "forest"),                             # Forest
    2: (_QGIS_ICON, "mIconVector.svg"),                        # Vector
    3: (_QGIS_ICON, "mIconRaster.svg"),                        # Raster
    6: (_QGIS_ICON, "sync_views.svg"),                         # Conversion
    7: (_QGIS_ICON, "mLayoutItem3DMap.svg"),                   # Elevation
    9: (_QGIS_ICON, "mActionIdentify.svg"),                    # Cadastre
    10: (_PLUGIN_ICON, "nextgis_logo.svg"),                    # Web GIS
    11: (_QGIS_ICON, "mActionAddImage.svg"),                   # Photo
    15: (_PLUGIN_ICON, "osm_logo.svg"),                        # OpenStreetMap
    16: (_PLUGIN_ICON, "nextgis_toolbox_plugin_logo.svg"),     # Test
    17: (_QGIS_ICON, "mSensor.svg"),                           # Remote sensing
    18: (_QGIS_ICON, "mActionFindReplace.svg"),                # Address
    19: (_QGIS_ICON, "mIconQgsProjectFile.svg"),               # QGIS
    20: (_QGIS_ICON, "mActionHistory.svg"),                    # Versioning
    21: (_QGIS_ICON, "mIconGps.svg"),                          # GPS tracks
}
# fmt: on


class NgToolboxPlugin(NgToolboxPluginInterface):
    """NextGIS Toolbox Plugin"""

    _notifier: Optional[MessageBarNotifier]
    _toolbox: Optional[Toolbox]

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

        self._processing_provider = None

        self._notifier = None
        self._toolbox = None

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
        self._toolbox = Toolbox()

        QTimer.singleShot(0, self._initialize_ui)

        self.initProcessing()
        self._load_settings()

        logger.debug("<b>End plugin initialization</b>")

    def initProcessing(self) -> None:
        """
        Initialize and register the Processing provider.
        """
        assert self._toolbox is not None
        self._processing_provider = NgToolboxPluginProcessingProvider(
            self._toolbox
        )
        QgsApplication.processingRegistry().addProvider(
            self._processing_provider
        )

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

        icon = plugin_icon("nextgis_toolbox_plugin_logo.svg")

        self._plugin_menu = QMenu(self.iface.mainWindow())
        self._plugin_menu.setTitle("NextGIS Toolbox Plugin")
        self._plugin_menu.setIcon(icon)

        self._tools_menu = QMenu(
            self.tr("NextGIS Toolbox Tools"),
            self._plugin_menu,
        )
        self._tools_menu.setIcon(icon)

        self._build_toolbox_menu(
            parent_menu=self._tools_menu,
            tools=self._toolbox.tools,
            tags=self._toolbox.tags,
            provider_id=self._processing_provider.id(),
        )

        self._about_action = QAction(
            QgsApplication.getThemeIcon("mActionPropertiesWidget.svg"),
            self.tr("About plugin…"),
            self.iface.mainWindow(),
        )
        self._about_action.triggered.connect(self.open_about_dialog)

        self._plugin_menu.addMenu(self._tools_menu)
        self._plugin_menu.addAction(self._about_action)

        self._show_action = QAction(
            icon,
            "NextGIS Toolbox Plugin",
            self.iface.mainWindow(),
        )
        self._show_action.setCheckable(True)
        self._show_action.toggled.connect(self.run)

        processing_menu.addMenu(self._plugin_menu)

        attributes_toolbar = self.iface.attributesToolBar()
        if attributes_toolbar is not None:
            attributes_toolbar.addAction(self._show_action)

        self._show_help_action = QAction(
            icon,
            PLUGIN_NAME,
        )
        self._show_help_action.triggered.connect(self.open_about_dialog)
        plugin_help_menu = self.iface.pluginHelpMenu()
        assert plugin_help_menu is not None
        plugin_help_menu.addAction(self._show_help_action)

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

        if self._processing_provider is not None:
            QgsApplication.processingRegistry().removeProvider(
                self._processing_provider
            )
            self._processing_provider = None

        logger.debug("<b>End plugin unloading</b>")

    def _load_settings(self) -> None:
        """Register the plugin settings page in the QGIS Options dialog."""
        self._options_factory = NgToolboxPluginSettingsPageFactory()
        iface.registerOptionsWidgetFactory(self._options_factory)

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

    def _build_toolbox_menu(
        self,
        parent_menu: QMenu,
        tools: List[Dict[str, Any]],
        tags: List[Dict[str, Any]],
        provider_id: str,
    ) -> None:
        """
        Populate plugin menu with a two-level tag → tool hierarchy.

        The first level contains one submenu per tag (category).  Each
        submenu contains one :class:`QAction` per tool assigned to that tag.
        Tools that belong to multiple tags appear in every matching submenu.

        :param parent_menu: The menu to populate (e.g. the plugin root menu).
        :param tools: Raw tool list from ``Toolbox.tools``.
        :param tags: Raw tag list from ``Toolbox.tags``.
        :param provider_id: Processing provider ID used to look up algorithms
            (e.g. ``"ngtoolbox"``).
        """
        tool_by_name: Dict[str, Dict[str, Any]] = {
            tool["name"]: tool
            for tool in tools
            if not tool.get("is_dev", False)
        }

        tools_by_tag: Dict[int, List[str]] = {}
        for tool in tools:
            if tool.get("is_dev", False):
                continue
            for tag_id in tool.get("tags", []):
                tools_by_tag.setdefault(tag_id, []).append(tool["name"])

        registry = QgsApplication.processingRegistry()

        for tag in sorted(tags, key=lambda tag: tag["alias"]):
            tag_id = tag["id"]
            tag_alias = tag["alias"]

            tool_names = tools_by_tag.get(tag_id, [])
            if not tool_names:
                continue

            category_menu = QMenu(tag_alias, parent_menu)
            category_menu.setIcon(self._category_icon(tag_id))
            category_menu.setToolTipsVisible(True)

            for tool_name in tool_names:
                tool = tool_by_name.get(tool_name)
                if tool is None:
                    continue

                algorithm_id = f"{provider_id}:{tool_name}"

                if registry.algorithmById(algorithm_id) is None:
                    logger.warning(
                        f"Algorithm '{algorithm_id}' not found in registry; "
                        "skipping menu entry."
                    )
                    continue

                action = QAction(
                    QgsApplication.getThemeIcon("processingAlgorithm.svg"),
                    tool["alias"],
                    parent_menu,
                )
                action.setToolTip(tool.get("description", ""))
                action.setStatusTip(tool.get("description", ""))

                def _on_triggered(
                    _checked: bool = False,
                    _algorithm_id: str = algorithm_id,
                ) -> None:
                    execAlgorithmDialog(_algorithm_id)

                action.triggered.connect(_on_triggered)
                category_menu.addAction(action)

            if not category_menu.isEmpty():
                parent_menu.addMenu(category_menu)

    def _category_icon(self, tag_id: int) -> QIcon:
        """
        Return a themed icon for a tag category by its stable API identifier.

        :param tag_id: Numeric tag identifier from the NextGIS Toolbox API.

        :returns: Resolved icon.
        """
        icon_source, icon_name = _CATEGORY_ICON_MAP.get(
            tag_id,
            (_QGIS_ICON, "processingModel.svg"),
        )

        if icon_source == _PLUGIN_ICON:
            icon = plugin_icon(icon_name)
        elif icon_source == _MATERIAL_ICON:
            icon = material_icon(icon_name, size=64)
        else:
            icon = qgis_icon(icon_name)

        if icon.isNull():
            return qgis_icon("processingModel.svg")

        return icon
