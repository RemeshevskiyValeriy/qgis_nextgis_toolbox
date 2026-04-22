from typing import TYPE_CHECKING

from qgis.core import QgsRuntimeProfiler

from nextgis_toolbox.core.settings import NgToolboxPluginSettings
from nextgis_toolbox.nextgis_toolbox_plugin_interface import (
    NgToolboxPluginInterface,
)

if TYPE_CHECKING:
    from qgis.gui import QgisInterface


def classFactory(_iface: "QgisInterface") -> NgToolboxPluginInterface:
    """Create and return an instance of the NextGIS Toolbox Plugin.

    :param _iface: QGIS interface instance passed by QGIS at plugin load.

    :returns: An instance of NgToolboxPluginInterface (plugin or stub).
    """
    settings = NgToolboxPluginSettings()

    try:
        with QgsRuntimeProfiler.profile("Import plugin"):  # type: ignore PylancereportAttributeAccessIssue
            from nextgis_toolbox.nextgis_toolbox_plugin import NgToolboxPlugin

        plugin = NgToolboxPlugin()
        settings.did_last_launch_fail = False

    except Exception as error:
        import copy

        from qgis.PyQt.QtCore import QTimer

        from nextgis_toolbox.core.exceptions import (
            NgToolboxPluginReloadAfterUpdateWarning,
        )
        from nextgis_toolbox.nextgis_toolbox_plugin_stub import (
            NgToolboxPluginStub,
        )

        error_copy = copy.deepcopy(error)
        exception = error_copy

        if not settings.did_last_launch_fail:
            # Sometimes after an update that changes the plugin structure,
            # the plugin may fail to load. Restarting QGIS helps.
            exception = NgToolboxPluginReloadAfterUpdateWarning()
            exception.__cause__ = error_copy

        settings.did_last_launch_fail = True

        plugin = NgToolboxPluginStub()

        def display_exception() -> None:
            plugin.notifier.display_exception(exception)

        QTimer.singleShot(0, display_exception)

    return plugin
