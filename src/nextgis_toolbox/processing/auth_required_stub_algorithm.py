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

from qgis.core import (
    QgsProcessingAlgorithm,
)

from nextgis_toolbox.ui.icon import qgis_icon


class AuthRequiredStubAlgorithm(QgsProcessingAlgorithm):
    """
    Stub algorithm shown when user is not authenticated.
    """

    def initAlgorithm(self, configuration=None):
        pass

    def name(self):
        return "authentication_required"

    def displayName(self):
        return "Authentication required"

    def icon(self):
        return qgis_icon("mIconDelete.svg")

    def processAlgorithm(self, parameters, context, feedback):
        return {}

    def createInstance(self):
        return AuthRequiredStubAlgorithm()
