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
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, cast

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

from nextgis_toolbox.about_dialog import AboutDialog
from nextgis_toolbox.core.constants import PACKAGE_NAME, PLUGIN_NAME
from nextgis_toolbox.core.exceptions import (
    NgToolboxPluginProcessingRequiredWarning,
)
from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.nextgis_toolbox.api.toolbox import Toolbox
from nextgis_toolbox.nextgis_toolbox.models.tool import ToolboxTag, ToolboxTool
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
    6: (_MATERIAL_ICON, "conversion"),                         # Conversion
    7: (_QGIS_ICON, "mLayoutItem3DMap.svg"),                   # Elevation
    9: (_QGIS_ICON, "mActionIdentify.svg"),                    # Cadastre
    10: (_PLUGIN_ICON, "nextgis_logo.svg"),                    # Web GIS
    11: (_QGIS_ICON, "mActionAddImage.svg"),                   # Photo
    15: (_PLUGIN_ICON, "osm_logo.svg"),                        # OpenStreetMap
    16: (_PLUGIN_ICON, "nextgis_toolbox_plugin_logo.svg"),     # Test
    17: (_QGIS_ICON, "mSensor.svg"),                           # Remote sensing
    18: (_MATERIAL_ICON, "address"),                           # Address
    19: (_QGIS_ICON, "mIconQgsProjectFile.svg"),               # QGIS
    20: (_QGIS_ICON, "mActionHistory.svg"),                    # Versioning
    21: (_QGIS_ICON, "mIconGps.svg"),                          # GPS tracks
}
# fmt: on


class NgToolboxPlugin(NgToolboxPluginInterface):
    """NextGIS Toolbox Plugin"""

    _notifier: Optional[MessageBarNotifier]
    _toolbox: Optional[Toolbox]

    def __init__(self, iface: QgisInterface) -> None:
        super().__init__(iface)

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

    def _load_ui(self) -> bool:
        """Initialize GUI elements."""
        logger.debug("<b>Start plugin initialization</b>")

        self._notifier = MessageBarNotifier(self)

        QTimer.singleShot(0, self._initialize_ui)

        self._load_settings()

        logger.debug("<b>End plugin initialization</b>")

        return True

    def _load_processing(self) -> bool:
        """
        Initialize and register the Processing provider.
        """
        self._toolbox = Toolbox()
        self._toolbox.load_tools()
        self._toolbox.load_tags()

        self._processing_provider = NgToolboxPluginProcessingProvider(
            self._toolbox
        )
        QgsApplication.processingRegistry().addProvider(
            self._processing_provider
        )
        return True

    def _initialize_ui(self) -> None:
        """
        Create plugin UI after QGIS main window initialization.
        """
        processing_menu = self._find_processing_menu()

        if processing_menu is None:
            self._handle_missing_processing_plugin()
            return

        self._create_plugin_menu()
        self._create_toolbox_menu()
        self._create_about_action()
        self._create_show_action()
        self._create_help_action()

        self._register_plugin_menu(processing_menu)
        self._register_toolbar_action()
        self._register_help_action()

    def _find_processing_menu(self) -> Optional[QMenu]:
        """
        Find QGIS Processing menu.

        :returns: Processing menu or None.
        """
        for menu in self.qgis_iface.mainWindow().findChildren(QMenu):
            if menu.objectName() == "processing":
                return menu

        return None

    def _handle_missing_processing_plugin(self) -> None:
        """
        Handle missing QGIS Processing plugin.
        """
        self._notifier.display_exception(
            NgToolboxPluginProcessingRequiredWarning()
        )

        logger.debug(
            "<b>Processing plugin is not enabled. "
            "NextGIS Toolbox Plugin initialization skipped</b>"
        )

    def _create_plugin_menu(self) -> None:
        """
        Create root plugin menu.
        """
        icon = plugin_icon("nextgis_toolbox_plugin_logo.svg")

        self._plugin_menu = QMenu(self.qgis_iface.mainWindow())

        self._plugin_menu.setTitle("NextGIS Toolbox Plugin")
        self._plugin_menu.setIcon(icon)

    def _create_toolbox_menu(self) -> None:
        """
        Create toolbox tools submenu.
        """
        assert self._plugin_menu is not None
        assert self._toolbox is not None
        assert self._processing_provider is not None

        icon = plugin_icon("nextgis_toolbox_plugin_logo.svg")

        self._tools_menu = QMenu(
            self.tr("NextGIS Toolbox Tools"),
            self._plugin_menu,
        )

        self._tools_menu.setIcon(icon)

        self._populate_toolbox_menu(
            parent_menu=self._tools_menu,
            tools=self._toolbox.tools,
            tags=self._toolbox.tags,
            provider_id=self._processing_provider.id(),
        )

        self._plugin_menu.addMenu(self._tools_menu)

    def _create_about_action(self) -> None:
        """
        Create About action.
        """
        assert self._plugin_menu is not None

        self._about_action = QAction(
            QgsApplication.getThemeIcon("mActionPropertiesWidget.svg"),
            self.tr("About plugin…"),
            self.qgis_iface.mainWindow(),
        )

        self._about_action.triggered.connect(self.open_about_dialog)

        self._plugin_menu.addAction(self._about_action)

    def _create_show_action(self) -> None:
        """
        Create main plugin toolbar action.
        """
        icon = plugin_icon("nextgis_toolbox_plugin_logo.svg")

        self._show_action = QAction(
            icon,
            "NextGIS Toolbox Plugin",
            self.qgis_iface.mainWindow(),
        )

        self._show_action.setCheckable(True)
        self._show_action.toggled.connect(self.run)

    def _create_help_action(self) -> None:
        """
        Create plugin help menu action.
        """
        icon = plugin_icon("nextgis_toolbox_plugin_logo.svg")

        self._show_help_action = QAction(
            icon,
            PLUGIN_NAME,
        )

        self._show_help_action.triggered.connect(self.open_about_dialog)

    def _register_plugin_menu(
        self,
        processing_menu: QMenu,
    ) -> None:
        """
        Register plugin menu in Processing menu.

        :param processing_menu: QGIS Processing menu.
        """
        assert self._plugin_menu is not None

        processing_menu.addMenu(self._plugin_menu)

    def _register_toolbar_action(self) -> None:
        """
        Register plugin toolbar action.
        """
        attributes_toolbar = self.qgis_iface.attributesToolBar()

        if attributes_toolbar is not None:
            attributes_toolbar.addAction(self._show_action)

    def _register_help_action(self) -> None:
        """
        Register plugin action in Help menu.
        """
        plugin_help_menu = self.qgis_iface.pluginHelpMenu()
        assert plugin_help_menu is not None
        plugin_help_menu.addAction(self._show_help_action)

    def _unload_ui(self) -> None:
        """
        Cleanup plugin UI.
        """
        logger.debug("<b>Start plugin unloading</b>")

        self._unregister_toolbar_action()
        self._unregister_plugin_menu()
        self._unregister_help_action()

        self._delete_actions()

        self._unload_dock_widget()
        self._unload_notifier()

        logger.debug("<b>End plugin unloading</b>")

    def _unregister_toolbar_action(self) -> None:
        """
        Remove plugin action from QGIS toolbar.
        """
        attributes_toolbar = self.qgis_iface.attributesToolBar()

        if attributes_toolbar is not None:
            attributes_toolbar.removeAction(self._show_action)

    def _unregister_plugin_menu(self) -> None:
        """
        Remove plugin menu from Processing menu.
        """
        if self._plugin_menu is None:
            return

        for menu in self.qgis_iface.mainWindow().findChildren(QMenu):
            if menu.objectName() == "processing":
                menu.removeAction(self._plugin_menu.menuAction())
                break

    def _unregister_help_action(self) -> None:
        """
        Remove plugin action from QGIS Help menu.
        """
        if self._show_help_action is None:
            return

        plugin_help_menu = self.qgis_iface.pluginHelpMenu()
        assert plugin_help_menu is not None
        plugin_help_menu.removeAction(self._show_help_action)

    def _delete_actions(self) -> None:
        """
        Delete plugin menus and actions.
        """
        if self._plugin_menu is not None:
            self._plugin_menu.deleteLater()
            self._plugin_menu = None

        if self._show_action is not None:
            self._show_action.deleteLater()
            self._show_action = None

        if self._about_action is not None:
            self._about_action.deleteLater()
            self._about_action = None

        if self._show_help_action is not None:
            self._show_help_action.deleteLater()
            self._show_help_action = None

    def _unload_dock_widget(self) -> None:
        """
        Unload dock widget.
        """
        if self._dock_widget is None:
            return

        self._dock_widget.unload_proc()

        self._dock_widget.close()
        self._dock_widget.deleteLater()

        self._dock_widget = None

    def _unload_notifier(self) -> None:
        """
        Delete notifier instance.
        """
        if self._notifier is None:
            return

        self._notifier.deleteLater()

        self._notifier = None

    def _unload_processing(self) -> None:
        """
        Remove Processing provider from QGIS registry.
        """
        if self._processing_provider is None:
            return

        QgsApplication.processingRegistry().removeProvider(
            self._processing_provider
        )

        self._processing_provider = None

    def _load_settings(self) -> None:
        """Register the plugin settings page in the QGIS Options dialog."""
        self._options_factory = NgToolboxPluginSettingsPageFactory()
        self.qgis_iface.registerOptionsWidgetFactory(self._options_factory)

    @pyqtSlot(bool)
    def run(self, checked: bool) -> None:
        """Toggle dock widget visibility.

        :param checked: Action state
        """
        if self._first_start and checked:
            self._first_start = False

            try:
                self._dock_widget = ToolboxDockWidget(
                    self.qgis_iface,
                    self.qgis_iface.mainWindow(),
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

            self.qgis_iface.addDockWidget(
                Qt.DockWidgetArea.RightDockWidgetArea,
                self._dock_widget,
            )

            right_docks = [
                dock
                for dock in self.qgis_iface.mainWindow().findChildren(
                    QDockWidget
                )
                if self.qgis_iface.mainWindow().dockWidgetArea(dock)
                == Qt.DockWidgetArea.RightDockWidgetArea
            ]

            if right_docks:
                self.qgis_iface.mainWindow().tabifyDockWidget(
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

    def _populate_toolbox_menu(
        self,
        parent_menu: QMenu,
        tools: List[ToolboxTool],
        tags: List[ToolboxTag],
        provider_id: str,
    ) -> None:
        """
        Populate plugin menu with toolbox categories and tools.

        :param parent_menu: Root menu to populate.
        :param tools: Loaded toolbox tools.
        :param tags: Loaded toolbox tags.
        :param provider_id: QGIS Processing provider identifier.
        """

        tool_by_name = self._index_tools_by_name(tools)
        tools_by_tag = self._group_tools_by_tag(tools)

        for tag in sorted(tags, key=lambda item: item.alias):
            self._populate_tag_menu(
                parent_menu=parent_menu,
                tag=tag,
                tool_by_name=tool_by_name,
                tools_by_tag=tools_by_tag,
                provider_id=provider_id,
            )

    def _populate_tag_menu(
        self,
        parent_menu: QMenu,
        tag: ToolboxTag,
        tool_by_name: Dict[str, ToolboxTool],
        tools_by_tag: Dict[int, List[str]],
        provider_id: str,
    ) -> None:
        """
        Populate menu for a single toolbox tag.

        :param parent_menu: Parent menu.
        :param tag: Toolbox tag.
        :param tool_by_name: Indexed tools by name.
        :param tools_by_tag: Mapping of tag IDs to tool names.
        :param provider_id: QGIS Processing provider identifier.
        """
        tool_names = tools_by_tag.get(tag.id, [])

        if not tool_names:
            return

        category_menu = self._create_category_menu(
            tag,
            parent_menu,
        )

        for tool_name in tool_names:
            self._add_tool_to_category_menu(
                category_menu=category_menu,
                tool_name=tool_name,
                tool_by_name=tool_by_name,
                provider_id=provider_id,
                parent_menu=parent_menu,
            )

        if not category_menu.isEmpty():
            parent_menu.addMenu(category_menu)

    def _add_tool_to_category_menu(
        self,
        category_menu: QMenu,
        tool_name: str,
        tool_by_name: Dict[str, ToolboxTool],
        provider_id: str,
        parent_menu: QMenu,
    ) -> None:
        """
        Add toolbox tool action to category menu.

        :param category_menu: Category submenu.
        :param tool_name: Toolbox tool identifier.
        :param tool_by_name: Indexed tools by name.
        :param provider_id: QGIS Processing provider identifier.
        :param parent_menu: Parent menu for QAction ownership.
        """
        tool = tool_by_name.get(tool_name)

        if tool is None:
            return

        algorithm_id = f"{provider_id}:{tool.name}"

        if not self._algorithm_exists(algorithm_id):
            logger.warning(
                f"Algorithm '{algorithm_id}' not found in registry; "
                "skipping menu entry."
            )
            return

        action = self._create_tool_action(
            tool,
            algorithm_id,
            parent_menu,
        )

        category_menu.addAction(action)

    def _algorithm_exists(
        self,
        algorithm_id: str,
    ) -> bool:
        """
        Check whether Processing algorithm exists in registry.

        :param algorithm_id: QGIS Processing algorithm identifier.

        :returns: True if algorithm exists.
        """
        registry = QgsApplication.processingRegistry()

        return registry.algorithmById(algorithm_id) is not None

    def _index_tools_by_name(
        self,
        tools: List[ToolboxTool],
    ) -> Dict[str, ToolboxTool]:
        """
        Build tool lookup mapping by tool name.

        :param tools: Toolbox tools.

        :returns: Mapping of tool name to toolbox tool.
        """
        return {tool.name: tool for tool in tools if not tool.is_dev}

    def _group_tools_by_tag(
        self,
        tools: List[ToolboxTool],
    ) -> Dict[int, List[str]]:
        """
        Group toolbox tools by tag identifier.

        :param tools: Toolbox tools.

        :returns: Mapping of tag ID to tool names.
        """
        tools_by_tag: Dict[int, List[str]] = {}

        for tool in tools:
            if tool.is_dev:
                continue

            for tag_id in tool.tag_ids:
                tools_by_tag.setdefault(tag_id, []).append(tool.name)

        return tools_by_tag

    def _create_category_menu(
        self,
        tag: ToolboxTag,
        parent_menu: QMenu,
    ) -> QMenu:
        """
        Create toolbox category submenu.

        :param tag: Toolbox tag.
        :param parent_menu: Parent menu.

        :returns: Configured category menu.
        """
        category_menu = QMenu(tag.alias, parent_menu)

        category_menu.setIcon(self._category_icon(tag.id))
        category_menu.setToolTipsVisible(True)

        return category_menu

    def _create_tool_action(
        self,
        tool: ToolboxTool,
        algorithm_id: str,
        parent_menu: QMenu,
    ) -> QAction:
        """
        Create toolbox tool action.

        :param tool: Toolbox tool.
        :param algorithm_id: QGIS Processing algorithm identifier.
        :param parent_menu: Parent menu.

        :returns: Configured QAction instance.
        """
        action = QAction(
            QgsApplication.getThemeIcon("processingAlgorithm.svg"),
            tool.alias,
            parent_menu,
        )

        action.setToolTip(tool.description or "")
        action.setStatusTip(tool.description or "")

        action.setData(algorithm_id)

        action.triggered.connect(self._start_tool)

        return action

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

    @pyqtSlot(bool)
    def _start_tool(self, _checked: bool) -> None:
        """
        Open QGIS Processing execution dialog for selected toolbox algorithm.

        :param _checked: QAction checked state (unused).
        """
        action = cast(QAction, self.sender())
        algorithm_id = action.data()

        execAlgorithmDialog(algorithm_id)
