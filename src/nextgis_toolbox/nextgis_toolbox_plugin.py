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

import sys
from typing import TYPE_CHECKING, Dict, List, Optional, cast

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
from qgis.PyQt.QtWidgets import QAction, QDockWidget, QMenu

from nextgis_toolbox.core.constants import PACKAGE_NAME, PLUGIN_NAME
from nextgis_toolbox.core.exceptions import (
    NextgisToolboxProcessingRequiredWarning,
)
from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.nextgis_toolbox.sdk.authentication import (
    ToolboxAuthentication,
    ToolboxTokenAuthentication,
)
from nextgis_toolbox.nextgis_toolbox.sdk.client import ToolboxApiClient
from nextgis_toolbox.nextgis_toolbox.tasks.api import TasksApi
from nextgis_toolbox.nextgis_toolbox.tasks.tasks_interface import (
    TasksInterface,
)
from nextgis_toolbox.nextgis_toolbox.tasks.tasks_manager import TasksManager
from nextgis_toolbox.nextgis_toolbox.tools.api import ToolsApi
from nextgis_toolbox.nextgis_toolbox.tools.models import (
    ToolboxTag,
    ToolboxTool,
)
from nextgis_toolbox.nextgis_toolbox.tools.tools_interface import (
    ToolsInterface,
)
from nextgis_toolbox.nextgis_toolbox.tools.tools_manager import ToolsManager
from nextgis_toolbox.nextgis_toolbox_interface import (
    NextgisToolboxInterface,
)
from nextgis_toolbox.nextgis_toolbox_window import ToolboxDockWidget
from nextgis_toolbox.notifier.message_bar_notifier import MessageBarNotifier
from nextgis_toolbox.processing.nextgis_toolbox_processing_provider import (
    NextgisToolboxProcessingProvider,
)
from nextgis_toolbox.settings.nextgis_toolbox_settings import (
    AuthenticationType,
    NextgisToolboxSettings,
)
from nextgis_toolbox.settings.nextgis_toolbox_settings_page import (
    NextgisToolboxSettingsPageFactory,
)
from nextgis_toolbox.ui.about_dialog import AboutDialog
from nextgis_toolbox.ui.icon import plugin_icon, toolbox_category_icon

if TYPE_CHECKING:
    from nextgis_toolbox.notifier.notifier_interface import (
        NotifierInterface,
    )


class NextgisToolboxPlugin(NextgisToolboxInterface):
    """NextGIS Toolbox"""

    _notifier: MessageBarNotifier
    _api_client: ToolboxApiClient
    _tools_manager: ToolsInterface
    _tasks_manager: TasksInterface

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

        self._notifier = None  # type: ignore

        self._processing_provider = None
        self._api_client = None  # type: ignore
        self._tools_manager = None  # type: ignore
        self._tasks_manager = None  # type: ignore

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

    @property
    def tools_manager(self) -> ToolsInterface:
        """Return the tools feature manager.

        :returns: Tools feature interface instance.

        :raises AssertionError: If tools manager is not initialized.
        """
        assert self._tools_manager is not None, (
            "Tools manager is not initialized"
        )
        return self._tools_manager

    @property
    def tasks_manager(self) -> TasksInterface:
        """Return the tasks feature manager.

        :returns: Tasks feature interface instance.

        :raises AssertionError: If tasks manager is not initialized.
        """
        assert self._tasks_manager is not None, (
            "Tasks manager is not initialized"
        )
        return self._tasks_manager

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
        self._api_client = self._create_api_client()
        self._tools_manager = ToolsManager(ToolsApi(self._api_client), self)
        self._tasks_manager = TasksManager(TasksApi(self._api_client), self)

        self._tools_manager.load()
        self._tasks_manager.load()

        self.settings_changed.connect(self._update_api_client)

        self._processing_provider = NextgisToolboxProcessingProvider(
            tools_manager=self._tools_manager,
            tasks_manager=self._tasks_manager,
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
            NextgisToolboxProcessingRequiredWarning()
        )

        logger.debug(
            "<b>Processing plugin is not enabled. "
            "NextGIS Toolbox initialization skipped</b>"
        )

    def _create_plugin_menu(self) -> None:
        """
        Create root plugin menu.
        """
        icon = plugin_icon()

        self._plugin_menu = QMenu(self.qgis_iface.mainWindow())

        self._plugin_menu.setTitle("NextGIS Toolbox")
        self._plugin_menu.setIcon(icon)

    def _create_toolbox_menu(self) -> None:
        """
        Create toolbox tools submenu.
        """
        assert self._plugin_menu is not None
        assert self._processing_provider is not None

        icon = plugin_icon()

        self._tools_menu = QMenu(
            self.tr("Tools"),
            self._plugin_menu,
        )

        self._tools_menu.setIcon(icon)

        self._populate_toolbox_menu(
            parent_menu=self._tools_menu,
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
        icon = plugin_icon()

        self._show_action = QAction(
            icon,
            "NextGIS Toolbox",
            self.qgis_iface.mainWindow(),
        )

        self._show_action.setCheckable(True)
        self._show_action.toggled.connect(self.run)

    def _create_help_action(self) -> None:
        """
        Create plugin help menu action.
        """
        icon = plugin_icon()

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

        del self._dock_widget

    def _unload_notifier(self) -> None:
        """
        Delete notifier instance.
        """
        if self._notifier is None:
            return

        self._notifier.deleteLater()

        del self._notifier

    def _unload_processing(self) -> None:
        """
        Remove Processing provider from QGIS registry.
        """
        if self._processing_provider is not None:
            QgsApplication.processingRegistry().removeProvider(
                self._processing_provider
            )

            self._processing_provider = None

        if self._tools_manager is not None:
            self._tools_manager.unload()
            self._tools_manager.deleteLater()
            del self._tools_manager

        if self._tasks_manager is not None:
            self._tasks_manager.unload()
            self._tasks_manager.deleteLater()
            del self._tasks_manager

        if self._api_client is not None:
            self._api_client.deleteLater()
            del self._api_client

    def _load_settings(self) -> None:
        """Register the plugin settings page in the QGIS Options dialog."""
        self._options_factory = NextgisToolboxSettingsPageFactory()
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
                    self.tr("Failed to initialize NextGIS Toolbox."),
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
        provider_id: str,
    ) -> None:
        """
        Populate plugin menu with toolbox categories and tools.

        :param parent_menu: Root menu to populate.
        :param provider_id: QGIS Processing provider identifier.
        """
        tools_by_tag = self._group_tools_by_tag(self.tools_manager.tools())

        for tag in sorted(
            self.tools_manager.tags(), key=lambda item: item.alias
        ):
            self._populate_tag_menu(
                parent_menu=parent_menu,
                tag=tag,
                tools_by_tag=tools_by_tag,
                provider_id=provider_id,
            )

    def _populate_tag_menu(
        self,
        parent_menu: QMenu,
        tag: ToolboxTag,
        tools_by_tag: Dict[int, List[ToolboxTool]],
        provider_id: str,
    ) -> None:
        """
        Populate menu for a single toolbox tag.

        :param parent_menu: Parent menu.
        :param tag: Toolbox tag.
        :param tools_by_tag: Mapping of tag IDs to toolbox tools.
        :param provider_id: QGIS Processing provider identifier.
        """
        tools = tools_by_tag.get(tag.id, [])

        if not tools:
            return

        category_menu = self._create_category_menu(
            tag,
            parent_menu,
        )

        for tool in tools:
            self._add_tool_to_category_menu(
                category_menu=category_menu,
                tool=tool,
                provider_id=provider_id,
                parent_menu=parent_menu,
            )

        if not category_menu.isEmpty():
            parent_menu.addMenu(category_menu)

    def _add_tool_to_category_menu(
        self,
        category_menu: QMenu,
        tool: ToolboxTool,
        provider_id: str,
        parent_menu: QMenu,
    ) -> None:
        """
        Add toolbox tool action to category menu.

        :param category_menu: Category submenu.
        :param tool: Toolbox tool model.
        :param provider_id: QGIS Processing provider identifier.
        :param parent_menu: Parent menu for QAction ownership.
        """
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

    def _group_tools_by_tag(
        self,
        tools: List[ToolboxTool],
    ) -> Dict[int, List[ToolboxTool]]:
        """
        Group toolbox tools by tag identifier.

        :param tools: Toolbox tool models.
        :returns: Mapping of tag ID to toolbox tools.
        """
        tools_by_tag: Dict[int, List[ToolboxTool]] = {}

        for tool in tools:
            if tool.is_dev:
                continue

            for tag in tool.tags:
                tools_by_tag.setdefault(tag.id, []).append(tool)

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

        category_menu.setIcon(toolbox_category_icon(tag.id))
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

    @pyqtSlot(bool)
    def _start_tool(self, _checked: bool) -> None:
        """
        Open QGIS Processing execution dialog for selected toolbox algorithm.

        :param _checked: QAction checked state (unused).
        """
        action = cast(QAction, self.sender())
        algorithm_id = action.data()

        execAlgorithmDialog(algorithm_id)

    def _create_authentication(
        self,
        authentication_type: AuthenticationType,
        authentication_token: Optional[str],
    ) -> Optional[ToolboxAuthentication]:
        """Create an authentication object from current settings."""
        if authentication_type != AuthenticationType.TOKEN:
            return None

        token = authentication_token
        if not token:
            return None

        return ToolboxTokenAuthentication(token)

    def _is_authentication_changed(
        self,
        authentication_type: AuthenticationType,
        authentication_token: Optional[str],
    ) -> bool:
        """Check whether client authentication differs from saved settings."""
        new_auth = self._create_authentication(
            authentication_type, authentication_token
        )

        return self._api_client.authentication != new_auth

    def _create_api_client(self) -> ToolboxApiClient:
        """Create and configure API client based on current settings."""
        settings = NextgisToolboxSettings()
        authentication_type = settings.authentication_type
        authentication_token = settings.authentication_token

        return ToolboxApiClient(
            self,
            endpoint=settings.endpoint,
            authentication=self._create_authentication(
                authentication_type, authentication_token
            ),
        )

    @pyqtSlot()
    def _update_api_client(self) -> None:
        """Update the shared API client only when connection settings change."""
        settings = NextgisToolboxSettings()
        endpoint_changed = self._api_client.endpoint != settings.endpoint
        authentication_changed = self._is_authentication_changed(
            settings.authentication_type, settings.authentication_token
        )

        if not endpoint_changed and not authentication_changed:
            logger.debug("Connection settings is unchanged")
            return

        if endpoint_changed:
            logger.debug("API client endpoint updated")
            self._api_client.endpoint = settings.endpoint

        if authentication_changed:
            logger.debug("API client authentication updated")
            self._api_client.authentication = self._create_authentication(
                settings.authentication_type, settings.authentication_token
            )
