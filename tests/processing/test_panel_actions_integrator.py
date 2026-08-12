from typing import cast
from unittest.mock import Mock

from qgis.PyQt.QtCore import QPoint, pyqtSignal
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QMenu, QToolBar, QToolButton, QWidget

from nextgis_toolbox.tools.models import ToolsManagerState
from nextgis_toolbox.nextgis_toolbox_interface import (
    NextgisToolboxInterface,
)
from nextgis_toolbox.processing.ui.compat import ProcessingToolbox
from nextgis_toolbox.processing.ui.panel_actions_integrator import (
    PanelActionsIntegrator,
)


class FakeProcessingToolbox(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.algorithmTree = FakeAlgorithmTree(self)
        self.processingToolbar = QToolBar(self)
        self.add_provider_calls = 0
        self.remove_provider_calls = 0

    def addProvider(self, _provider_id: str) -> None:  # noqa: N802
        self.add_provider_calls += 1

    def removeProvider(self, _provider_id: str) -> None:  # noqa: N802
        self.remove_provider_calls += 1


class FakeAlgorithmTree(QWidget):
    customContextMenuRequested = pyqtSignal(QPoint)

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self._index = Mock()
        self.algorithmForIndex = Mock(return_value=None)

    def indexAt(self, point: QPoint):
        del point
        return self._index

    def mapToGlobal(self, a0):
        return a0


def _create_integrator(qgis_iface) -> PanelActionsIntegrator:
    provider = Mock()
    provider.id.return_value = "nextgis_toolbox"
    provider.name.return_value = "NextGIS Toolbox"
    provider.icon.return_value = QIcon()
    return PanelActionsIntegrator(qgis_iface=qgis_iface, provider=provider)


def _add_button(toolbar: QToolBar, object_name: str) -> None:
    button = QToolButton(toolbar)
    button.setObjectName(object_name)
    toolbar.addWidget(button)


def _button_order(toolbar: QToolBar) -> list:
    object_names = []

    for toolbar_action in toolbar.actions():
        widget = toolbar.widgetForAction(toolbar_action)
        if isinstance(widget, QToolButton):
            object_names.append(widget.objectName())

    return object_names


def test_sync_provider_actions_creates_button_manually(
    qgis_iface,
    qgis_app,
    monkeypatch,
) -> None:
    del qgis_app

    plugin = Mock()
    plugin.tools_manager.state = ToolsManagerState.LOADED
    monkeypatch.setattr(
        NextgisToolboxInterface,
        "instance",
        classmethod(lambda cls: plugin),
    )

    integrator = _create_integrator(qgis_iface)
    toolbox = FakeProcessingToolbox(qgis_iface.mainWindow())
    toolbar = toolbox.processingToolbar

    _add_button(toolbar, "provideraction_native")
    _add_button(toolbar, "provideraction_script")
    _add_button(toolbar, "provideraction_buffer")

    integrator._sync_provider_actions(cast(ProcessingToolbox, toolbox))

    assert toolbox.add_provider_calls == 0
    assert toolbox.remove_provider_calls == 0
    assert _button_order(toolbar) == [
        "provideraction_native",
        "provideraction_script",
        "provideraction_nextgis_toolbox",
        "provideraction_buffer",
    ]

    button = toolbox.findChild(QToolButton, "provideraction_nextgis_toolbox")
    assert button is not None
    assert button.menu() is not None
    assert [action.text() for action in button.menu().actions()] == [
        "Open in Browser",
        "Tasks history",
        "Refresh tools",
        "Settings…",
        "About…",
    ]


def test_sync_provider_actions_reuses_existing_button(
    qgis_iface,
    qgis_app,
    monkeypatch,
) -> None:
    del qgis_app

    plugin = Mock()
    plugin.tools_manager.state = ToolsManagerState.LOADED
    monkeypatch.setattr(
        NextgisToolboxInterface,
        "instance",
        classmethod(lambda cls: plugin),
    )

    integrator = _create_integrator(qgis_iface)
    toolbox = FakeProcessingToolbox(qgis_iface.mainWindow())
    toolbar = toolbox.processingToolbar

    _add_button(toolbar, "provideraction_native")
    _add_button(toolbar, "provideraction_script")
    _add_button(toolbar, "provideraction_buffer")

    integrator._sync_provider_actions(cast(ProcessingToolbox, toolbox))

    first_button = toolbox.findChild(
        QToolButton, "provideraction_nextgis_toolbox"
    )
    assert first_button is not None
    assert first_button.menu() is not None
    assert first_button.menu().actions()[2].isEnabled() is True

    plugin.tools_manager.state = ToolsManagerState.LOADING
    integrator._sync_provider_actions(cast(ProcessingToolbox, toolbox))

    second_button = toolbox.findChild(
        QToolButton, "provideraction_nextgis_toolbox"
    )
    assert second_button is first_button
    assert _button_order(toolbar) == [
        "provideraction_native",
        "provideraction_script",
        "provideraction_nextgis_toolbox",
        "provideraction_buffer",
    ]
    assert toolbar.findChildren(QToolButton, "provideraction_nextgis_toolbox") == [
        first_button
    ]
    assert second_button.menu() is not None
    assert second_button.menu().actions()[2].isEnabled() is False


def test_sync_provider_actions_appends_button_when_script_anchor_missing(
    qgis_iface,
    qgis_app,
    monkeypatch,
) -> None:
    del qgis_app

    plugin = Mock()
    plugin.tools_manager.state = ToolsManagerState.LOADED
    monkeypatch.setattr(
        NextgisToolboxInterface,
        "instance",
        classmethod(lambda cls: plugin),
    )

    integrator = _create_integrator(qgis_iface)
    toolbox = FakeProcessingToolbox(qgis_iface.mainWindow())
    toolbar = toolbox.processingToolbar

    _add_button(toolbar, "provideraction_native")

    integrator._sync_provider_actions(cast(ProcessingToolbox, toolbox))

    assert _button_order(toolbar) == [
        "provideraction_native",
        "provideraction_nextgis_toolbox",
    ]


def test_provider_context_menu_shows_only_for_provider_item(
    qgis_iface,
    qgis_app,
    monkeypatch,
) -> None:
    del qgis_app

    plugin = Mock()
    plugin.tools_manager.state = ToolsManagerState.LOADED
    monkeypatch.setattr(
        NextgisToolboxInterface,
        "instance",
        classmethod(lambda cls: plugin),
    )

    integrator = _create_integrator(qgis_iface)
    toolbox = FakeProcessingToolbox(qgis_iface.mainWindow())
    index = Mock()
    index.isValid.return_value = True
    index.data.return_value = "NextGIS Toolbox"
    toolbox.algorithmTree._index = index

    shown_menus = []

    def fake_exec(menu_self, point) -> None:
        shown_menus.append((menu_self, point))

    monkeypatch.setattr(QMenu, "exec", fake_exec)

    integrator._connect_context_menu(cast(ProcessingToolbox, toolbox))
    toolbox.algorithmTree.customContextMenuRequested.emit(QPoint(5, 7))

    assert len(shown_menus) == 1
    assert [action.text() for action in shown_menus[0][0].actions()] == [
        "Open in Browser",
        "Tasks history",
        "Refresh tools",
        "Settings…",
        "About…",
    ]

    shown_menus.clear()
    toolbox.algorithmTree.algorithmForIndex.return_value = Mock()
    toolbox.algorithmTree.customContextMenuRequested.emit(QPoint(5, 7))
    assert shown_menus == []

    toolbox.algorithmTree.algorithmForIndex.return_value = None
    index.data.return_value = "Native"
    toolbox.algorithmTree.customContextMenuRequested.emit(QPoint(5, 7))
    assert shown_menus == []
