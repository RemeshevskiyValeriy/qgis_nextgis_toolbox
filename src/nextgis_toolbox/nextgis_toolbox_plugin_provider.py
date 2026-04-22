# NextGIS Toolbox Plugin
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

import traceback

from qgis.core import Qgis, QgsMessageLog, QgsProcessingProvider
from qgis.utils import iface

from nextgis_toolbox.algorithm_factory import algorithm_class_factory
from nextgis_toolbox.nextgis_toolbox import Toolbox


class NgPluginProvider(QgsProcessingProvider):
    def __init__(self, toolbox: Toolbox):
        QgsProcessingProvider.__init__(self)
        self.toolbox = toolbox

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        toolbox_io, errors = self.toolbox.get_toolbox_interface()
        if errors:
            iface.messageBar().pushMessage(
                self.tr("Error uploading some tools! Check log for details"),
                level=Qgis.Warning,
            )
            for tool, err in errors.items():
                QgsMessageLog.logMessage(
                    f"Error uploading tool {tool}. Exception: {err}",
                    "NgToolbox",
                    level=Qgis.Warning,
                )
        tags = {tag["id"]: tag for tag in self.toolbox.tags}

        try:
            for tool in self.toolbox.tools:
                if tool["is_dev"]:
                    continue
                io = toolbox_io[tool["operation_id"]]
                group = self.tr("Other")
                if tool["tags"]:
                    # qgis not allow one tool in multiple groups
                    # so take only 1st tag as group
                    group = tags[tool["tags"][0]]["name"]

                alg = algorithm_class_factory(
                    tool["operation_id"],
                    tool["name"],
                    group,
                    tool["description"],
                    io["inputs"],
                    io["outputs"],
                    self.toolbox,
                )
                self.addAlgorithm(alg())
        except Exception:
            err = traceback.format_exc()
            iface.messageBar().pushMessage(
                self.tr(
                    "Error adding NGToolbox to QGIS processing! Check log for details"
                ),
                level=Qgis.Critical,
            )
            QgsMessageLog.logMessage(
                f"Error adding NGToolbox to QGIS processing! Exception: {err}",
                "NgToolbox",
                level=Qgis.Critical,
            )

    def id(self):
        return "ngtoolbox"

    def name(self):
        return "NextGis Toolbox"

    def icon(self):
        return QgsProcessingProvider.icon(self)

    def longName(self):
        return self.name()
