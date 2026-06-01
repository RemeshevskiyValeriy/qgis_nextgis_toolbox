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

from typing import TYPE_CHECKING, Optional

from processing import execAlgorithmDialog
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtWidgets import QAction, QMenu

from nextgis_toolbox.nextgis_toolbox.tools.models import ToolsManagerState
from nextgis_toolbox.processing.ui.algorithm_dialog_manager import (
    AlgorithmDialogManager,
)
from nextgis_toolbox.processing.ui.favorite_tools_sync import (
    FavoriteToolsSync,
)
from nextgis_toolbox.processing.ui.menu_bar_actions_integrator import (
    ToolboxMenuBarIntegrator,
)
from nextgis_toolbox.processing.ui.panel_actions_integrator import (
    PanelActionsIntegrator,
)
from nextgis_toolbox.ui.icon import plugin_icon

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

    from nextgis_toolbox.nextgis_toolbox.sdk.client import ToolboxApiClient
    from nextgis_toolbox.nextgis_toolbox.tools.tools_interface import (
        ToolsInterface,
    )
    from nextgis_toolbox.processing.nextgis_toolbox_processing_provider import (
        NextgisToolboxProcessingProvider,
    )


class ToolboxProviderUi(QObject):
    """Own Processing-specific provider actions, menus and runtime UI."""

    def __init__(
        self,
        provider: "NextgisToolboxProcessingProvider",
        qgis_iface: "QgisInterface",
        api_client: "ToolboxApiClient",
        tools_manager: "ToolsInterface",
        parent: Optional[QObject] = None,
    ) -> None:
        """Initialize provider and Processing-specific runtime UI."""
        super().__init__(parent)
        self._provider = provider
        self._qgis_iface = qgis_iface
        self._api_client = api_client
        self._tools_manager = tools_manager

        self._dialog_manager = None
        self._panel_actions_integrator = None
        self._menu_bar_integrator = None
        self._favorite_tool_sync = None

        self._menu = None
        self._refresh_action = None
        self._is_loaded = False

    def load(self) -> None:
        """Register provider actions and connect dialog patching."""
        if self._is_loaded:
            return

        self._dialog_manager = AlgorithmDialogManager(self)
        self._provider.algorithm_instance_created.connect(
            self._dialog_manager.on_algorithm_instance_created
        )

        self._panel_actions_integrator = PanelActionsIntegrator(
            qgis_iface=self._qgis_iface,
            provider=self._provider,
            parent=self,
        )
        self._panel_actions_integrator.load()

        self._menu_bar_integrator = ToolboxMenuBarIntegrator(
            qgis_iface=self._qgis_iface,
            tools_manager=self._tools_manager,
            provider_id=self._provider.id(),
            start_tool_callback=self._start_tool,
            parent=self,
        )
        self._favorite_tool_sync = FavoriteToolsSync(
            api_client=self._api_client,
            tools_manager=self._tools_manager,
            provider_id=self._provider.id(),
            parent=self,
        )

        self._tools_manager.state_changed.connect(
            self._on_runtime_state_changed
        )
        self._is_loaded = True

        self._on_runtime_state_changed(self._tools_manager.state)

    def unload(self) -> None:
        """Release provider bindings and Processing runtime UI resources."""
        if not self._is_loaded:
            return
        self._is_loaded = False

        self._favorite_tool_sync.stop()
        self._favorite_tool_sync.deleteLater()

        self._panel_actions_integrator.unload()
        self._panel_actions_integrator.deleteLater()
        self._menu_bar_integrator.unload()
        self._menu_bar_integrator.deleteLater()

        self._provider.algorithm_instance_created.disconnect(
            self._dialog_manager.on_algorithm_instance_created
        )
        self._tools_manager.state_changed.disconnect(
            self._on_runtime_state_changed
        )

        self._refresh_action = None

        if self._menu is not None:
            self._menu.deleteLater()
            self._menu = None

    def create_tools_menu(self, parent_menu: QMenu) -> QMenu:
        """Create the toolbox submenu under the plugin menu."""
        if self._menu is not None:
            return self._menu

        tools_menu = QMenu(self.tr("Tools"), parent_menu)
        tools_menu.setIcon(plugin_icon())
        self._menu_bar_integrator.bind_tools_menu(tools_menu)
        tools_menu.aboutToShow.connect(
            self._menu_bar_integrator.refresh_tools_menu
        )
        self._menu_bar_integrator.refresh()
        parent_menu.addMenu(tools_menu)
        self._menu = tools_menu
        return tools_menu

    def set_refresh_action(self, action: QAction) -> None:
        """Bind the refresh action for enabled-state updates."""
        self._refresh_action = action
        action.setEnabled(
            self._tools_manager.state != ToolsManagerState.LOADING
        )

    def refresh_actions(self) -> None:
        self._menu_bar_integrator.refresh()
        self._panel_actions_integrator.refresh()

    def _on_runtime_state_changed(self, state: ToolsManagerState) -> None:
        if state == ToolsManagerState.LOADED:
            self._favorite_tool_sync.start()
        else:
            self._favorite_tool_sync.stop()

        self.refresh_actions()

        if self._refresh_action is not None:
            self._refresh_action.setEnabled(state != ToolsManagerState.LOADING)

    def _start_tool(self, _checked: bool) -> None:
        action = self.sender()
        if not isinstance(action, QAction):
            return

        execAlgorithmDialog(action.data())
