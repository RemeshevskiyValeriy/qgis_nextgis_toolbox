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

from qgis.core import QgsProcessingParameterBoolean
from qgis.PyQt.QtCore import QCoreApplication

EMAIL_NOTIFICATION_PARAMETER_NAME = "nextgis_toolbox_email_notification"
ADD_RESULTS_TO_PROJECT_PARAMETER_NAME = (
    "nextgis_toolbox_add_results_to_project"
)


class ProcessingControlParameterFactory:
    def create_email_notification(self) -> QgsProcessingParameterBoolean:
        parameter = QgsProcessingParameterBoolean(
            EMAIL_NOTIFICATION_PARAMETER_NAME,
            QCoreApplication.translate(
                "ToolboxAlgorithm",
                "Notify by email when the task is completed",
            ),
            defaultValue=False,
        )
        parameter.setHelp(
            QCoreApplication.translate(
                "ToolboxAlgorithm",
                "Send a notification email when the remote task finishes.",
            )
        )
        return parameter

    def create_add_to_project(self) -> QgsProcessingParameterBoolean:
        parameter = QgsProcessingParameterBoolean(
            ADD_RESULTS_TO_PROJECT_PARAMETER_NAME,
            QCoreApplication.translate(
                "ToolboxAlgorithm",
                "Add downloaded outputs to the project",
            ),
            defaultValue=False,
        )
        parameter.setHelp(
            QCoreApplication.translate(
                "ToolboxAlgorithm",
                "Try to load downloaded geodata outputs into the current project.",
            )
        )
        return parameter
