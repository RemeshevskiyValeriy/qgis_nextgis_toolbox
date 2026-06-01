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

from typing import Callable, Dict, List, Optional, Set, Tuple, cast

from processing.core.ProcessingConfig import ProcessingConfig, Setting
from processing.gui import menus as processing_menus
from qgis.core import QgsApplication, QgsProcessingAlgorithm
from qgis.gui import QgisInterface
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMainWindow, QMenu

from nextgis_toolbox.nextgis_toolbox.tools.models import (
    ToolboxTag,
    ToolboxTool,
    ToolsManagerState,
)
from nextgis_toolbox.nextgis_toolbox.tools.tools_interface import (
    ToolsInterface,
)
from nextgis_toolbox.processing.utils import toolbox_algorithm_id
from nextgis_toolbox.ui.icon import (
    plugin_icon,
    qgis_icon,
    toolbox_category_icon,
)


class ToolboxMenuBarIntegrator(QObject):
    _TOOL_MENU_PATHS: Dict[str, str] = {}

    def __init__(
        self,
        qgis_iface: QgisInterface,
        tools_manager: ToolsInterface,
        provider_id: str,
        start_tool_callback: Callable,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._qgis_iface = qgis_iface
        self._tools_manager = tools_manager
        self._provider_id = provider_id
        self._start_tool_callback = start_tool_callback
        self._integrated_menu_paths: Dict[str, str] = {}
        self._processing_placeholder_entries: List[Tuple[QMenu, QAction]] = []
        self._registered_setting_names: Set[str] = set()
        self._patched_default_entries: Set[str] = set()
        self._tools_menu: Optional[QMenu] = None

    def bind_tools_menu(self, tools_menu: QMenu) -> None:
        self._tools_menu = tools_menu

    def refresh(self) -> None:
        self._clear_processing_menu_entries()
        self._clear_processing_placeholder_entries()
        self._remove_registered_settings()
        self._clear_patched_defaults()
        self._refresh_processing_menu_entries()
        self.refresh_tools_menu()

    def unload(self) -> None:
        self._clear_processing_menu_entries()
        self._clear_processing_placeholder_entries()
        self._remove_registered_settings()
        self._clear_patched_defaults()

        if self._tools_menu is not None:
            self._tools_menu.clear()

    def refresh_tools_menu(self) -> None:
        if self._tools_menu is None:
            return

        self._tools_menu.clear()
        self.populate_toolbox_menu(self._tools_menu)

    def populate_toolbox_menu(self, parent_menu: QMenu) -> None:
        if self._tools_manager.state != ToolsManagerState.LOADED:
            self._add_placeholder_action(parent_menu)
            return

        self._add_dynamic_tool_sections(parent_menu)

        separator_action = None
        if not parent_menu.isEmpty():
            separator_action = parent_menu.addSeparator()

        added_tag_sections = 0
        for tag in self._tools_manager.tags():
            tools = self._tools_manager.find_tools(tag=tag)
            if not tools:
                continue

            category_menu = self._create_category_menu(tag, parent_menu)
            for tool in tools:
                if not self._algorithm_exists(tool.name):
                    continue

                category_menu.addAction(
                    self._create_tool_action(tool, category_menu)
                )

            if not category_menu.isEmpty():
                parent_menu.addMenu(category_menu)
                added_tag_sections += 1

        if separator_action is not None and added_tag_sections == 0:
            parent_menu.removeAction(separator_action)

    def integrate_tool(self, tool: ToolboxTool) -> None:
        if not self._algorithm_exists(tool.name):
            return

        algorithm_id = toolbox_algorithm_id(self._provider_id, tool.name)
        menu_path = self._register_menu_settings(tool)
        if not menu_path:
            return

        self._add_processing_menu_entry(algorithm_id, menu_path)

    def _refresh_processing_menu_entries(self) -> None:
        if self._tools_manager.state != ToolsManagerState.LOADED:
            self._add_processing_placeholder_entry()
            return

        for tool in self._tools_manager.tools():
            self.integrate_tool(tool)

    def _clear_processing_menu_entries(self) -> None:
        for algorithm_id, menu_path in list(
            self._integrated_menu_paths.items()
        ):
            menu_name, submenu_name = self._split_menu_path(menu_path)
            processing_menus.removeAlgorithmEntry(
                algorithm_id,
                menu_name,
                submenu_name,
                delButton=False,
            )

        self._integrated_menu_paths.clear()

    def _remove_registered_settings(self) -> None:
        for setting_name in self._registered_setting_names:
            if setting_name not in ProcessingConfig.settings:
                continue

            ProcessingConfig.removeSetting(setting_name)

        self._registered_setting_names.clear()

    def _clear_patched_defaults(self) -> None:
        for algorithm_id in self._patched_default_entries:
            processing_menus.defaultMenuEntries.pop(algorithm_id, None)

        self._patched_default_entries.clear()

    def _register_menu_settings(self, tool: ToolboxTool) -> str:
        algorithm_id = toolbox_algorithm_id(self._provider_id, tool.name)
        default_menu_path = self._default_menu_path(tool)
        if default_menu_path:
            processing_menus.defaultMenuEntries[algorithm_id] = (
                default_menu_path
            )
            self._patched_default_entries.add(algorithm_id)

        settings_to_add = (
            Setting(
                processing_menus.menusSettingsGroup,
                f"MENU_{algorithm_id}",
                "Menu path",
                default_menu_path,
            ),
            Setting(
                processing_menus.menusSettingsGroup,
                f"BUTTON_{algorithm_id}",
                "Add button",
                False,
            ),
            Setting(
                processing_menus.menusSettingsGroup,
                f"ICON_{algorithm_id}",
                "Icon",
                "",
                valuetype=Setting.FILE,
            ),
        )

        for setting in settings_to_add:
            ProcessingConfig.addSetting(setting)
            setting.read()
            self._registered_setting_names.add(setting.name)

        configured_menu_path = ProcessingConfig.getSetting(
            f"MENU_{algorithm_id}"
        )
        return (
            "" if configured_menu_path is None else str(configured_menu_path)
        )

    def _default_menu_path(self, tool: ToolboxTool) -> str:
        algorithm_id = toolbox_algorithm_id(self._provider_id, tool.name)
        default_menu_path = self._TOOL_MENU_PATHS.get(algorithm_id)
        if default_menu_path:
            return default_menu_path

        default_menu_path = self._TOOL_MENU_PATHS.get(tool.name)
        if default_menu_path:
            return default_menu_path

        return self._tag_menu_path(tool)

    def _tag_menu_path(self, tool: ToolboxTool) -> str:
        tag_ids = set(tool.tag_ids)
        for required_tag_ids, menu_path in self._tag_menu_paths():
            if required_tag_ids.issubset(tag_ids):
                return menu_path

        return ""

    def _tag_menu_paths(self) -> Tuple[Tuple[frozenset, str], ...]:
        return (
            (frozenset([10]), f"{self._web_menu_title()}/NextGIS Web"),
            (
                frozenset([2, 6]),
                f"{self._qgis_iface.vectorMenu().title()}/"
                f"{processing_menus.Processing.tr('&Data Management Tools')}",
            ),
        )

    def _add_processing_menu_entry(
        self,
        algorithm_id: str,
        menu_path: str,
    ) -> None:
        algorithm = self._processing_algorithm(algorithm_id)
        if algorithm is None:
            return

        menu_name, submenu_name = self._split_menu_path(menu_path)
        if not menu_name:
            return

        processing_menus.addAlgorithmEntry(
            algorithm,
            menu_name,
            submenu_name,
            icon=plugin_icon("algorithm.svg"),
        )
        self._integrated_menu_paths[algorithm_id] = menu_path

    def _split_menu_path(self, menu_path: str) -> Tuple[str, str]:
        paths = menu_path.split("/")
        menu_name = paths[0]
        submenu_name = paths[-1] if len(paths) > 1 else ""
        return menu_name, submenu_name

    def _add_dynamic_tool_sections(self, parent_menu: QMenu) -> None:
        self._add_tool_section(
            parent_menu=parent_menu,
            section_title=self.tr("Favorites"),
            icon=qgis_icon("mIconFavorites.svg"),
            tools=self._tools_manager.find_tools(is_favorite=True),
        )
        self._add_tool_section(
            parent_menu=parent_menu,
            section_title=self.tr("Recommendations"),
            icon=QIcon(),
            tools=self._tools_manager.find_tools(is_featured=True),
        )

    def _add_tool_section(
        self,
        *,
        parent_menu: QMenu,
        section_title: str,
        icon: QIcon,
        tools: List[ToolboxTool],
    ) -> None:
        if not tools:
            return

        section_menu = QMenu(section_title, parent_menu)
        if not icon.isNull():
            section_menu.setIcon(icon)

        for tool in tools:
            if not self._algorithm_exists(tool.name):
                continue

            section_menu.addAction(
                self._create_tool_action(tool, section_menu)
            )

        if not section_menu.isEmpty():
            parent_menu.addMenu(section_menu)

    def _create_category_menu(
        self,
        tag: ToolboxTag,
        parent_menu: QMenu,
    ) -> QMenu:
        category_menu = QMenu(tag.alias, parent_menu)
        category_menu.setIcon(toolbox_category_icon(tag.id))
        category_menu.setToolTipsVisible(True)
        return category_menu

    def _create_tool_action(
        self,
        tool: ToolboxTool,
        parent_menu: QMenu,
    ) -> QAction:
        algorithm_id = toolbox_algorithm_id(self._provider_id, tool.name)
        action = QAction(
            plugin_icon("algorithm.svg"),
            tool.alias,
            parent_menu,
        )
        action.setToolTip(tool.description or "")
        action.setStatusTip(tool.description or "")
        action.setData(algorithm_id)
        action.triggered.connect(self._start_tool_callback)
        return action

    def _algorithm_exists(self, tool_name: str) -> bool:
        return (
            self._processing_algorithm(
                toolbox_algorithm_id(self._provider_id, tool_name)
            )
            is not None
        )

    def _add_processing_placeholder_entry(self) -> None:
        menu_name, submenu_name = self._split_menu_path(
            self._placeholder_menu_path()
        )
        menu = processing_menus.getMenu(
            menu_name,
            cast(QMainWindow, self._qgis_iface.mainWindow()).menuBar(),
        )
        submenu = processing_menus.getMenu(submenu_name, menu)
        action = QAction(
            self._placeholder_icon(),
            self._placeholder_text(),
            submenu,
        )
        action.setEnabled(False)
        action.setToolTip(self._placeholder_tooltip())
        action.setStatusTip(self._placeholder_tooltip())
        submenu.addAction(action)
        self._processing_placeholder_entries.append((submenu, action))

    def _add_placeholder_action(self, parent_menu: QMenu) -> None:
        action = QAction(
            self._placeholder_icon(),
            self._placeholder_text(),
            parent_menu,
        )
        action.setEnabled(False)
        action.setToolTip(self._placeholder_tooltip())
        action.setStatusTip(self._placeholder_tooltip())
        parent_menu.addAction(action)

    def _placeholder_icon(self) -> QIcon:
        return qgis_icon("mActionRefresh.svg")

    def _placeholder_menu_path(self) -> str:
        return f"{self._web_menu_title()}/{self.tr('NextGIS Toolbox')}"

    def _placeholder_text(self) -> str:
        if self._is_catalog_loading():
            return self.tr("Loading tools…")

        return self.tr("Failed to load tools")

    def _placeholder_tooltip(self) -> str:
        if self._is_catalog_loading():
            return self.tr("The tools catalog is still loading.")

        if self._tools_manager.error is not None:
            return str(self._tools_manager.error)

        return self.tr("Failed to load tools. Use Refresh tools to try again.")

    def _clear_processing_placeholder_entries(self) -> None:
        for submenu, action in self._processing_placeholder_entries:
            try:
                if sip.isdeleted(submenu):
                    continue

                if not sip.isdeleted(action):
                    submenu.removeAction(action)

                if not submenu.actions():
                    submenu.deleteLater()
            except RuntimeError:
                continue

        self._processing_placeholder_entries.clear()

    def _is_catalog_loading(self) -> bool:
        return self._tools_manager.state in (
            ToolsManagerState.INITIALIZATION,
            ToolsManagerState.LOADING,
        )

    def _processing_algorithm(
        self, algorithm_id: str
    ) -> Optional[QgsProcessingAlgorithm]:
        return QgsApplication.processingRegistry().algorithmById(algorithm_id)

    def _web_menu_title(self) -> str:
        web_menu = getattr(self._qgis_iface, "webMenu", None)
        if callable(web_menu):
            menu = web_menu()
            if isinstance(menu, QMenu):
                return menu.title()

        return "web"
