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

from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING

from nextgis_toolbox.core.constants import PLUGIN_NAME
from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.core.utils import PluginRuntimeProfiler
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
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.debug(
        "-" * 40 + f" Loading {PLUGIN_NAME} plugin ({time}) " + "-" * 40
    )
    PluginRuntimeProfiler.reset()
    return _create_instance(iface)


def _create_instance(iface: "QgisInterface") -> NextgisToolboxInterface:
    settings = NextgisToolboxSettings()

    try:
        plugin = _create_plugin_instance(iface)
        settings.did_last_launch_fail = False

    except Exception as error:
        logger.exception(
            "Failed to create plugin instance",
            exc_info=error,
        )
        plugin = _create_stub_instance(iface, error, settings)
        settings.did_last_launch_fail = True

    return plugin


def _create_plugin_instance(iface: "QgisInterface") -> NextgisToolboxInterface:
    with PluginRuntimeProfiler("plugin import"):
        from nextgis_toolbox.nextgis_toolbox_plugin import (
            NextgisToolboxPlugin,
        )

    with PluginRuntimeProfiler("plugin creation"):
        plugin = NextgisToolboxPlugin(iface)  # pyright: ignore[reportPossiblyUnboundVariable]

    return plugin  # pyright: ignore[reportPossiblyUnboundVariable]


def _create_stub_instance(
    iface: "QgisInterface", error: Exception, settings: NextgisToolboxSettings
) -> NextgisToolboxInterface:
    import copy

    from qgis.PyQt.QtCore import QTimer

    from nextgis_toolbox.core.exceptions import (
        ToolboxReloadAfterUpdateWarning,
    )
    from nextgis_toolbox.nextgis_toolbox_interface import (
        NextgisToolboxPluginStub,
    )

    with PluginRuntimeProfiler("stub creation"):
        error_copy = copy.deepcopy(error)
        exception = error_copy

        if not settings.did_last_launch_fail:
            # Sometimes after an update that changes the plugin structure,
            # the plugin may fail to load. Restarting QGIS helps.
            exception = ToolboxReloadAfterUpdateWarning()
            exception.__cause__ = error_copy

        plugin = NextgisToolboxPluginStub(iface)

        QTimer.singleShot(0, partial(_display_exception, error))

    return plugin  # pyright: ignore[reportPossiblyUnboundVariable]


def _display_exception(error: Exception) -> None:
    plugin = NextgisToolboxInterface.instance()
    plugin.notifier.display_exception(error)
