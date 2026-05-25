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

from qgis.core import QgsRuntimeProfiler

from nextgis_toolbox.nextgis_toolbox_interface import (
    NextgisToolboxInterface,
)
from nextgis_toolbox.settings.nextgis_toolbox_settings import (
    NextgisToolboxSettings,
)

if TYPE_CHECKING:
    from qgis.gui import QgisInterface


def classFactory(iface: "QgisInterface") -> NextgisToolboxInterface:
    """Create and return an instance of the NextGIS Toolbox.

    :param iface: QGIS interface instance passed by QGIS at plugin load.

    :returns: An instance of NextgisToolboxInterface (plugin or stub).
    """
    settings = NextgisToolboxSettings()

    try:
        with QgsRuntimeProfiler.profile("Import plugin"):  # type: ignore PylancereportAttributeAccessIssue
            from nextgis_toolbox.nextgis_toolbox_plugin import (
                NextgisToolboxPlugin,
            )

        plugin = NextgisToolboxPlugin(iface)
        settings.did_last_launch_fail = False

    except Exception as error:
        import copy

        from qgis.PyQt.QtCore import QTimer

        from nextgis_toolbox.core.exceptions import (
            NextgisToolboxReloadAfterUpdateWarning,
        )
        from nextgis_toolbox.nextgis_toolbox_interface import (
            NextgisToolboxPluginStub,
        )

        error_copy = copy.deepcopy(error)
        exception = error_copy

        if not settings.did_last_launch_fail:
            # Sometimes after an update that changes the plugin structure,
            # the plugin may fail to load. Restarting QGIS helps.
            exception = NextgisToolboxReloadAfterUpdateWarning()
            exception.__cause__ = error_copy

        settings.did_last_launch_fail = True

        plugin = NextgisToolboxPluginStub(iface)

        def display_exception() -> None:
            plugin.notifier.display_exception(exception)

        QTimer.singleShot(0, display_exception)

    return plugin
