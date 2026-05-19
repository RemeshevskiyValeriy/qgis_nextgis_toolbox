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

from typing import TYPE_CHECKING, Dict

from qgis.core import Qgis, QgsProcessingProvider, QgsRuntimeProfiler
from qgis.PyQt.QtGui import QIcon

from nextgis_toolbox.core.constants import PLUGIN_NAME
from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.notifier.message_bar_notifier import MessageBarNotifier
from nextgis_toolbox.processing.nextgis_toolbox_algorithm import (
    NextgisToolboxAlgorithm,
)
from nextgis_toolbox.ui.icon import plugin_icon

if TYPE_CHECKING:
    from nextgis_toolbox.nextgis_toolbox.tasks.tasks_interface import (
        TasksInterface,
    )
    from nextgis_toolbox.nextgis_toolbox.tools.models import ToolboxTool
    from nextgis_toolbox.nextgis_toolbox.tools.tools_interface import (
        ToolsInterface,
    )


class NextgisToolboxProcessingProvider(QgsProcessingProvider):
    """
    QGIS Processing provider for NextGIS Toolbox tools.
    """

    def __init__(
        self,
        tools_manager: "ToolsInterface",
        tasks_manager: "TasksInterface",
    ) -> None:
        """
        Initialize plugin processing provider.

        :param tools_manager: Tools feature interface.
        :param tasks_manager: Tasks feature interface.
        """
        super().__init__()
        self._tools_manager = tools_manager
        self._tasks_manager = tasks_manager

        self._notifier = MessageBarNotifier(self)

    def unload(self) -> None:
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self) -> None:
        """
        Fetch tool I/O definitions from the API and register algorithms.
        """

        with QgsRuntimeProfiler.profile(
            f"load algs: {len(self._tools_manager.tools())}"
        ):  # type: ignore PylancereportAttributeAccessIssue
            load_errors = self._load_tool_algorithms()

            if not load_errors:
                return

            self._notify_load_errors(load_errors)

    def id(self) -> str:
        """
        Return provider ID.

        :returns: Unique provider identifier.
        """
        return "nextgistoolbox"

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

    def _load_tool_algorithms(self) -> Dict[str, str]:
        """
        Load and register toolbox Processing algorithms.

        :returns: Mapping of tool name to error message.
        """
        load_errors: Dict[str, str] = {}

        for tool in self._tools_manager.tools():
            if tool.is_dev or tool.name != "hello":
                continue

            try:
                self._add_tool_algorithm(tool)

            except Exception as error:
                load_errors[tool.name] = str(error)

        return load_errors

    def _add_tool_algorithm(
        self,
        tool: "ToolboxTool",
    ) -> None:
        """
        Create and register Processing algorithm for toolbox tool.

        :param tool: Toolbox tool descriptor.
        """
        inputs, outputs = self._tools_manager.fetch_tool_io_parameters(
            tool.name
        )

        algorithm = NextgisToolboxAlgorithm(
            tool_id=tool.name,
            display_name=tool.alias,
            description=tool.description,
            inputs=inputs,
            outputs=outputs,
            tasks_manager=self._tasks_manager,
        )

        self.addAlgorithm(algorithm)

    def _notify_load_errors(
        self,
        load_errors: Dict[str, str],
    ) -> None:
        """
        Notify user about failed toolbox algorithm loading.

        :param load_errors: Mapping of tool name to error message.
        """
        self._notifier.display_message(
            self.tr(
                "Some tools could not be loaded. See plugin logs for details."
            ),
            level=Qgis.MessageLevel.Warning,
        )

        for tool_name, message in load_errors.items():
            logger.warning(f"Failed to load tool '{tool_name}': {message}")
