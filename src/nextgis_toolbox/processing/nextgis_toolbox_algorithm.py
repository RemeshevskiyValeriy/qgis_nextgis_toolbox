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

from time import sleep
from typing import Any, Dict, Optional

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingContext,
)
from qgis.PyQt.QtCore import QCoreApplication

from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.core.utils import nextgis_domain
from nextgis_toolbox.nextgis_toolbox.tasks.models import TaskStatus
from nextgis_toolbox.nextgis_toolbox.tasks.tasks_interface import (
    TasksInterface,
)
from nextgis_toolbox.nextgis_toolbox.tools.models import (
    ToolboxTool,
)
from nextgis_toolbox.processing.parameter_mapping import (
    create_input_parameter,
    create_ngw_connection_parameters,
    create_output_parameter,
    resolve_parameter_value,
)
from nextgis_toolbox.processing.utils import (
    format_tool_description,
    format_tool_help,
)


class NextgisToolboxAlgorithm(QgsProcessingAlgorithm):
    """
    Processing algorithm for a single NextGIS Toolbox tool.
    """

    _tool: ToolboxTool
    _tasks_manager: "TasksInterface"

    def __init__(
        self,
        tool: ToolboxTool,
        tasks_manager: TasksInterface,
    ) -> None:
        """
        Initialize processing algorithm.

        :param tool: Toolbox tool descriptor.
        :param tasks_manager: Tasks feature interface.
        """
        super().__init__()

        self._tool = tool
        self._tasks_manager = tasks_manager

    def initAlgorithm(
        self,
        configuration: Optional[Dict[Optional[str], Any]] = None,
    ) -> None:
        """
        Declare algorithm parameters and outputs.

        :param configuration: Optional provider configuration dict
            (unused, required by base class API).
        """
        for input_parameter in self._tool.inputs:
            if input_parameter.parameter_type == "ngw_connection":
                for qgis_parameter in create_ngw_connection_parameters(
                    input_parameter
                ):
                    self.addParameter(qgis_parameter)
            else:
                self.addParameter(create_input_parameter(input_parameter))

        for output_param in self._tool.outputs:
            self.addOutput(create_output_parameter(output_param))

    def processAlgorithm(
        self,
        parameters: Dict[Optional[str], Any],
        context: QgsProcessingContext,
        feedback,
    ) -> Dict[str, Any]:
        """
        Execute processing algorithm.

        :param parameters: Processing parameters.
        :param context: Processing context.
        :param feedback: Processing feedback.

        :returns: Processing result.
        """
        logger.info(f"Running tool '{self._tool.name}'")

        resolved_parameters: Dict[str, Any] = {
            input_parameter.name: resolve_parameter_value(
                input_parameter, self, parameters, context
            )
            for input_parameter in self._tool.inputs
        }

        task_id = self._tasks_manager.submit_task(
            self._tool.name,
            resolved_parameters,
        )

        feedback.setProgress(1)

        while not feedback.isCanceled():
            try:
                task = self._tasks_manager.retrieve_task(task_id)
            except Exception as error:
                logger.exception(
                    (f"Failed to retrieve task '{task_id}' status"),
                    exc_info=error,
                )
                raise

            state = task.state

            if state == TaskStatus.SUCCESS:
                logger.info(f"Tool '{self._tool.name}' finished successfully")

                feedback.setProgress(100)
                return {}

            if state == TaskStatus.FAILED:
                error_message = task.error

                logger.warning(
                    (
                        f"Tool '{self._tool.name}' failed. Error: {error_message}"
                    )
                )

                raise Exception(error_message)

            feedback.pushInfo(self.tr("Waiting for processing results..."))

            feedback.setProgress(int(task.progress))

            sleep(3)

        feedback.pushInfo(
            self.tr(
                "Execution was canceled. "
                "The task continues on the server side."
            )
        )

        logger.warning(
            f"Tool '{self._tool.name}' execution was canceled by user"
        )

        return {}

    def name(self) -> str:
        """
        Return internal algorithm identifier.

        :returns: Algorithm identifier.
        """
        return self._tool.name

    def displayName(self) -> str:
        """
        Return visible algorithm name.

        :returns: Display name.
        """
        return self._tool.alias

    def shortDescription(self) -> str:
        """
        Return algorithm short description.

        :returns: Short description.
        """
        return format_tool_description(self._tool)

    def shortHelpString(self) -> str:
        """
        Return algorithm help text.

        :returns: Help text.
        """
        return format_tool_help(self._tool)

    def helpUrl(self) -> str:
        """Return URL to the tool documentation.

        :returns: Documentation URL based on the current locale.
        """
        return (
            nextgis_domain("docs")
            + f"/docs_toolbox/source/{self._tool.name}.html"
        )

    def createInstance(self) -> "NextgisToolboxAlgorithm":
        """
        Create new algorithm instance.

        :returns: New algorithm instance.
        """
        return type(self)(
            tool=self._tool,
            tasks_manager=self._tasks_manager,
        )

    def tr(self, text: str) -> str:
        """
        Translate a string via Qt's translation system.

        :param text: Source string.

        :returns: Translated string.
        """
        return QCoreApplication.translate(self.__class__.__name__, text)
