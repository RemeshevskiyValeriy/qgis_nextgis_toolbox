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

from typing import TYPE_CHECKING, List, Optional

from qgis.core import Qgis, QgsProcessingProvider
from qgis.PyQt.QtCore import pyqtSignal

from nextgis_toolbox.core.constants import PACKAGE_NAME, PLUGIN_NAME
from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.core.utils import PluginRuntimeProfiler
from nextgis_toolbox.nextgis_toolbox_interface import NextgisToolboxInterface
from nextgis_toolbox.processing.parameters import (
    ProcessingParameterRegistry,
    create_default_parameter_registry,
)
from nextgis_toolbox.processing.parameters.common import (
    InputParameterAdapter,
    OutputParameterAdapter,
)
from nextgis_toolbox.processing.toolbox_algorithm import (
    ToolboxAlgorithm,
)
from nextgis_toolbox.processing.toolbox_status_algorithm import (
    ToolboxStatusAlgorithm,
)
from nextgis_toolbox.processing.ui.compat import IS_DESKTOP_PLATFORM
from nextgis_toolbox.settings.nextgis_toolbox_settings import (
    AuthenticationType,
)
from nextgis_toolbox.tools.models import (
    InputParameterType,
    OutputParameterType,
    ToolsManagerState,
)

if TYPE_CHECKING or IS_DESKTOP_PLATFORM:
    from qgis.PyQt.QtGui import QIcon

    from nextgis_toolbox.processing.ui.provider_ui import ToolboxProviderUi
    from nextgis_toolbox.ui.icon import plugin_icon
else:
    ToolboxProviderUi = object
    QIcon = object

    def plugin_icon() -> object:
        return object()


if TYPE_CHECKING:
    from nextgis_toolbox.tasks.tasks_interface import (
        TasksInterface,
    )
    from nextgis_toolbox.tools.models import ToolboxTool
    from nextgis_toolbox.tools.tools_interface import (
        ToolsInterface,
    )


class NextgisToolboxProcessingProvider(QgsProcessingProvider):
    """
    QGIS Processing provider for NextGIS Toolbox tools.
    """

    algorithm_instance_created = pyqtSignal(object)

    def __init__(
        self,
        tools_manager: "ToolsInterface",
        tasks_manager: "TasksInterface",
        parameter_registry: Optional[ProcessingParameterRegistry] = None,
    ) -> None:
        """
        Initialize plugin processing provider.

        :param tools_manager: Tools feature interface.
        :param tasks_manager: Tasks feature interface.
        """
        super().__init__()
        self._tools_manager = tools_manager
        self._tasks_manager = tasks_manager
        self._parameter_registry = (
            parameter_registry or create_default_parameter_registry()
        )
        self._tools_manager.state_changed.connect(
            self._on_tools_manager_state_changed
        )
        self._provider_ui = None

    def load(self) -> bool:
        return super().load()

    def unload(self) -> None:
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        self._provider_ui = None

    def set_provider_ui(self, provider_ui: "ToolboxProviderUi") -> None:
        """Attach the desktop runtime UI used by provider actions."""
        self._provider_ui = provider_ui

    def loadAlgorithms(self) -> None:
        """
        Register cached toolbox tools as Processing algorithms.
        """

        if self._tools_manager.state != ToolsManagerState.LOADED:
            self.addAlgorithm(
                ToolboxStatusAlgorithm(
                    self._tools_manager.state,
                    self._tools_manager.error,
                )
            )
            return

        with PluginRuntimeProfiler(
            f"load {len(self._tools_manager.tools())} tool algorithms"
        ):
            load_errors = self._load_tool_algorithms()

            if not load_errors:
                return

            self._notify_load_errors(load_errors)

    def id(self) -> str:
        """
        Return provider ID.

        :returns: Unique provider identifier.
        """
        return PACKAGE_NAME

    def name(self) -> str:
        """
        Return provider short name.

        :returns: Provider name.
        """
        return PLUGIN_NAME

    def icon(self) -> QIcon:
        return plugin_icon()

    def longName(self) -> str:
        """
        Return provider full name.

        :returns: Full provider name.
        """
        return self.name()

    def warningMessage(self) -> str:
        if (
            self._tasks_manager.api().api_client.authentication_type
            != AuthenticationType.NONE
        ):
            return super().warningMessage()

        return self.tr(
            "Tool execution is unavailable due to missing authentication."
            " Please set your API key in plugin settings."
        )

    @property
    def parameter_registry(self) -> ProcessingParameterRegistry:
        """Return the parameter adapter registry.

        :returns: Processing parameter registry.
        """
        return self._parameter_registry

    def register_input_parameter_adapter(
        self,
        parameter_type: InputParameterType,
        adapter: InputParameterAdapter,
        *,
        prepend: bool = False,
    ) -> None:
        """Register an input parameter adapter.

        :param parameter_type: Input parameter type to extend.
        :param adapter: Adapter implementation.
        :param prepend: Register before built-in adapters.
        """
        self._parameter_registry.register_input_adapter(
            parameter_type,
            adapter,
            prepend=prepend,
        )

    def register_output_parameter_adapter(
        self,
        parameter_type: OutputParameterType,
        adapter: OutputParameterAdapter,
        *,
        prepend: bool = False,
    ) -> None:
        """Register an output parameter adapter.

        :param parameter_type: Output parameter type to extend.
        :param adapter: Adapter implementation.
        :param prepend: Register before built-in adapters.
        """
        self._parameter_registry.register_output_adapter(
            parameter_type,
            adapter,
            prepend=prepend,
        )

    def _load_tool_algorithms(self) -> List[str]:
        """
        Load and register toolbox Processing algorithms.

        :returns: Mapping of tool name to error message.
        """
        load_errors: List[str] = []

        for tool in self._tools_manager.tools():
            try:
                self._add_tool_algorithm(tool)

            except Exception:
                logger.exception(f"Failed to load tool '{tool.name}'")
                load_errors.append(tool.name)

        return load_errors

    def _add_tool_algorithm(
        self,
        tool: "ToolboxTool",
    ) -> None:
        """
        Create and register Processing algorithm for toolbox tool.

        :param tool: Toolbox tool descriptor.
        """
        algorithm = ToolboxAlgorithm(
            tool,
            self._tasks_manager,
            parameter_registry=self._parameter_registry,
        )
        self.addAlgorithm(algorithm)

    def _notify_load_errors(
        self,
        load_errors: List[str],
    ) -> None:
        """
        Notify user about failed toolbox algorithm loading.

        :param load_errors: List of tool names that failed to load.
        """
        plugin = NextgisToolboxInterface.instance()
        plugin.notifier.display_message(
            self.tr(
                f"{len(load_errors)} tools could not be loaded. See plugin logs for details."
            ),
            level=Qgis.MessageLevel.Warning,
        )

    def _on_tools_manager_state_changed(
        self,
        _state: ToolsManagerState,
    ) -> None:
        self.refreshAlgorithms()
