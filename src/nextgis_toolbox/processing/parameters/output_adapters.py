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

from typing import TYPE_CHECKING

from qgis.core import (
    QgsProcessingOutputString,
    QgsProcessingParameterFileDestination,
)
from qgis.PyQt.QtCore import QCoreApplication

from nextgis_toolbox.processing.parameters.common import (
    OutputParameterAdapter,
    OutputParameterRepresentation,
    apply_parameter_help,
)
from nextgis_toolbox.tools.models import (
    OutputParameterType,
    ToolOutputParameter,
)

if TYPE_CHECKING:
    from nextgis_toolbox.processing.parameters.registry import (
        OutputParameterAdapterRegistry,
    )


class GenericOutputAdapter(OutputParameterAdapter):
    def create_representation(
        self,
        parameter: ToolOutputParameter,
    ) -> OutputParameterRepresentation:
        return OutputParameterRepresentation(
            outputs=[
                QgsProcessingOutputString(
                    parameter.name,
                    parameter.label,
                )
            ],
            parameters=[],
        )


class FileOutputAdapter(OutputParameterAdapter):
    def create_representation(
        self,
        parameter: ToolOutputParameter,
    ) -> OutputParameterRepresentation:
        qgis_parameter = QgsProcessingParameterFileDestination(
            parameter.name,
            parameter.label,
            fileFilter=QCoreApplication.translate(
                "ToolboxAlgorithm",
                "All files (*.*)",
            ),
            optional=True,
        )
        return OutputParameterRepresentation(
            outputs=[],
            parameters=[
                apply_parameter_help(
                    qgis_parameter,
                    parameter.description,
                )
            ],
        )


class OutputParameterAdapterFactory:
    def __init__(self) -> None:
        self._generic_adapter = GenericOutputAdapter()
        self._file_adapter = FileOutputAdapter()

    def register_defaults(
        self, registry: "OutputParameterAdapterRegistry"
    ) -> None:
        for parameter_type in (
            OutputParameterType.STRING,
            OutputParameterType.INTEGER,
            OutputParameterType.FLOAT,
            OutputParameterType.BOOLEAN,
            OutputParameterType.DATE,
            OutputParameterType.BBOX,
        ):
            registry.register(parameter_type, self._generic_adapter)

        registry.register(OutputParameterType.FILE, self._file_adapter)
