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

from typing import TYPE_CHECKING, Callable, Dict, List, Optional

from qgis.PyQt.QtCore import QObject, QPoint
from qgis.PyQt.QtWidgets import (
    QAction,
    QMenu,
    QToolBar,
    QToolButton,
    QWidget,
)

from nextgis_toolbox.core.utils import assert_not_none
from nextgis_toolbox.processing.ui.compat import (
    ProcessingToolbox,
    ProviderContextMenuActions,
)
from nextgis_toolbox.processing.ui.provider_actions import (
    ContextAction,
    OpenProviderAboutAction,
    OpenProviderInBrowserAction,
    OpenProviderSettingsAction,
    OpenProviderTasksHistoryAction,
    OpenToolDocumentationAction,
    OpenToolInBrowserAction,
    RefreshProviderToolsAction,
    ToolboxAction,
)

if TYPE_CHECKING:
    from qgis.gui import QgisInterface

    from nextgis_toolbox.processing.nextgis_toolbox_processing_provider import (
        NextgisToolboxProcessingProvider,
    )


class PanelActionsIntegrator(QObject):
    """Own provider action registration and toolbox button syncing."""

    def __init__(
        self,
        qgis_iface: "QgisInterface",
        provider: "NextgisToolboxProcessingProvider",
        parent: Optional[QObject] = None,
    ) -> None:
        """Initialize provider action integration."""
        super().__init__(parent)
        self._qgis_iface = qgis_iface
        self._provider = provider
        self._button_actions: List[ToolboxAction] = (
            self._create_provider_button_actions()
        )
        self._tool_actions: List[ContextAction] = (
            self._create_context_menu_actions()
        )
        self._toolboxes: Dict[int, ProcessingToolbox] = {}
        self._context_menu_handlers: Dict[int, Callable[[QPoint], None]] = {}
        self._is_loaded = False

    def load(self) -> None:
        """Register provider actions and integrate them into open toolboxes."""
        if self._is_loaded:
            self.refresh()
            return

        ProviderContextMenuActions.registerProviderContextMenuActions(
            self._tool_actions
        )
        self._is_loaded = True
        self.refresh()

    def unload(self) -> None:
        """Unregister provider actions and detach them from toolboxes."""
        if not self._is_loaded:
            return

        for toolbox in list(self._toolboxes.values()):
            self._remove_provider_button(toolbox)
            self._disconnect_context_menu(toolbox)

        self._toolboxes.clear()
        ProviderContextMenuActions.deregisterProviderContextMenuActions(
            self._tool_actions
        )
        self._is_loaded = False

    def refresh(self) -> None:
        """Refresh provider action state for all open Processing toolboxes."""
        if not self._is_loaded:
            return

        main_window = assert_not_none(
            self._qgis_iface.mainWindow(),
            "QGIS main window is unavailable",
        )
        for toolbox in self._find_toolboxes(main_window):
            self._bind_toolbox(toolbox)

    def _create_provider_button_actions(self) -> List[ToolboxAction]:
        """Create provider actions exposed by the Processing toolbar."""
        return [
            OpenProviderInBrowserAction(),
            OpenProviderTasksHistoryAction(),
            RefreshProviderToolsAction(),
            OpenProviderSettingsAction(),
            OpenProviderAboutAction(),
        ]

    def _create_context_menu_actions(self) -> List[ContextAction]:
        """Create tool context menu actions exposed by Processing."""
        return [
            OpenToolInBrowserAction(),
            OpenToolDocumentationAction(),
        ]

    def _find_toolboxes(self, root: QObject) -> List[ProcessingToolbox]:
        toolboxes: List[ProcessingToolbox] = []
        if isinstance(root, ProcessingToolbox):
            toolboxes.append(root)

        toolboxes.extend(root.findChildren(ProcessingToolbox))
        return toolboxes

    def _bind_toolbox(self, toolbox: ProcessingToolbox) -> None:
        toolbox_id = id(toolbox)
        if toolbox_id in self._toolboxes:
            self._sync_provider_actions(toolbox)
            return

        toolbox.destroyed.connect(
            lambda *_args, current_toolbox_id=toolbox_id: self._forget_toolbox(
                current_toolbox_id
            )
        )
        self._toolboxes[toolbox_id] = toolbox
        self._connect_context_menu(toolbox)
        self._sync_provider_actions(toolbox)

    def _forget_toolbox(self, toolbox_id: int) -> None:
        toolbox = self._toolboxes.pop(toolbox_id, None)
        handler = self._context_menu_handlers.pop(toolbox_id, None)
        if toolbox is not None and handler is not None:
            toolbox.algorithmTree.customContextMenuRequested.disconnect(
                handler
            )

    def _sync_provider_actions(self, toolbox: ProcessingToolbox) -> None:
        button = self._provider_button(toolbox)
        if button is None:
            self._add_provider_button(toolbox)
            return

        self._update_provider_button(button, toolbox)

    def _remove_provider_button(self, toolbox: ProcessingToolbox) -> None:
        # ProcessingToolbox.addProvider/removeProvider are buggy, so keep
        # provider button lifecycle fully manual.
        toolbar = toolbox.processingToolbar
        provider_id = self._provider.id()
        button_action = self._toolbar_action(
            toolbar, f"provideraction_{provider_id}"
        )

        if button_action is None:
            return

        toolbar.removeAction(button_action)

    def _add_provider_button(
        self,
        toolbox: ProcessingToolbox,
    ) -> Optional[QToolButton]:
        toolbar = toolbox.processingToolbar
        anchor_action = self._toolbar_action(toolbar, "provideraction_script")
        provider_id = self._provider.id()

        button = QToolButton(toolbar)
        button.setObjectName(f"provideraction_{provider_id}")
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._update_provider_button(button, toolbox)
        if anchor_action is None:
            toolbar.addWidget(button)
        else:
            actions = list(toolbar.actions())
            anchor_index = actions.index(anchor_action)
            target_action = None
            if anchor_index + 1 < len(actions):
                target_action = actions[anchor_index + 1]

            if target_action is None:
                toolbar.addWidget(button)
            else:
                toolbar.insertWidget(target_action, button)

        return button

    def _update_provider_button(
        self,
        button: QToolButton,
        toolbox: ProcessingToolbox,
    ) -> None:
        provider_name = self._provider.name()

        button.setIcon(self._provider.icon())
        button.setToolTip(provider_name)

        menu = button.menu()
        if menu is None or len(menu.actions()) != len(self._button_actions):
            menu = self._create_provider_menu(button, toolbox)
            button.setMenu(menu)
            return

        menu.setTitle(provider_name)
        menu.setObjectName(f"{provider_name}_menu")
        for menu_action, provider_action in zip(
            menu.actions(),
            self._button_actions,
        ):
            menu_action.setText(provider_action.name)
            menu_action.setObjectName(provider_action.name)
            menu_action.setIcon(provider_action.getIcon())
            menu_action.setEnabled(provider_action.isEnabled())

    def _execute_provider_action(
        self,
        provider_action: ToolboxAction,
        toolbox: ProcessingToolbox,
    ) -> None:
        provider_action.setData(toolbox)
        provider_action.execute()

    def _connect_context_menu(
        self,
        toolbox: ProcessingToolbox,
    ) -> None:
        toolbox_id = id(toolbox)
        if toolbox_id in self._context_menu_handlers:
            return

        handler = lambda point, current_toolbox=toolbox: (  # noqa: E731
            self._show_provider_context_menu(current_toolbox, point)
        )
        toolbox.algorithmTree.customContextMenuRequested.connect(handler)
        self._context_menu_handlers[toolbox_id] = handler

    def _disconnect_context_menu(
        self,
        toolbox: ProcessingToolbox,
    ) -> None:
        toolbox_id = id(toolbox)
        handler = self._context_menu_handlers.pop(toolbox_id, None)
        if handler is None:
            return

        toolbox.algorithmTree.customContextMenuRequested.disconnect(handler)

    def _show_provider_context_menu(
        self,
        toolbox: ProcessingToolbox,
        point: QPoint,
    ) -> None:
        index = toolbox.algorithmTree.indexAt(point)
        if not index.isValid():
            return

        if toolbox.algorithmTree.algorithmForIndex(index) is not None:
            return

        item_name = index.data()
        if not isinstance(item_name, str):
            return

        if item_name != self._provider.name():
            return

        menu = self._create_provider_menu(toolbox, toolbox)
        menu.exec(toolbox.algorithmTree.mapToGlobal(point))

    def _create_provider_menu(
        self,
        parent: QWidget,
        toolbox: ProcessingToolbox,
    ) -> QMenu:
        menu = QMenu(self._provider.name(), parent)
        menu.setObjectName(f"{self._provider.name()}_menu")

        for provider_action in self._button_actions:
            action = QAction(provider_action.name, menu)
            action.setObjectName(provider_action.name)
            action.setIcon(provider_action.getIcon())
            action.setEnabled(provider_action.isEnabled())
            action.triggered.connect(
                lambda _checked=False, current_action=provider_action, current_toolbox=toolbox: (
                    self._execute_provider_action(
                        current_action,
                        current_toolbox,
                    )
                )
            )
            menu.addAction(action)

        return menu

    def _toolbar_action(
        self,
        toolbar: QToolBar,
        object_name: str,
    ) -> Optional[QAction]:
        for toolbar_action in list(toolbar.actions()):
            widget = toolbar.widgetForAction(toolbar_action)
            if not isinstance(widget, QToolButton):
                continue

            if widget.objectName() == object_name:
                return toolbar_action

        return None

    def _provider_button(
        self,
        toolbox: ProcessingToolbox,
    ) -> Optional[QToolButton]:
        return toolbox.findChild(
            QToolButton, f"provideraction_{self._provider.id()}"
        )
