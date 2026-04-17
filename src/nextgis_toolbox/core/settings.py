from qgis.core import QgsSettings

from nextgis_toolbox.core.constants import PLUGIN_SETTINGS_GROUP


class NgToolboxPluginSettings:
    """Centralized settings handler for the NextGIS Toolbox Plugin."""

    KEY_IS_DEBUG_LOGS_ENABLED = (
        f"{PLUGIN_SETTINGS_GROUP}/other/debugLogsEnabled"
    )
    KEY_DID_LAST_LAUNCH_FAIL = (
        f"{PLUGIN_SETTINGS_GROUP}/other/didLastLaunchFail"
    )

    __settings: QgsSettings

    def __init__(self) -> None:
        self.__settings = QgsSettings()

    @property
    def is_debug_logs_enabled(self) -> bool:
        """Check if debug logs are enabled."""
        return self.__settings.value(
            self.KEY_IS_DEBUG_LOGS_ENABLED,
            defaultValue=True,
            type=bool,
        )

    @is_debug_logs_enabled.setter
    def is_debug_logs_enabled(self, value: bool) -> None:
        self.__settings.setValue(self.KEY_IS_DEBUG_LOGS_ENABLED, value)

    @property
    def did_last_launch_fail(self) -> bool:
        """Checks whether the last plugin launch failed."""
        return self.__settings.value(
            self.KEY_DID_LAST_LAUNCH_FAIL,
            defaultValue=False,
            type=bool,
        )

    @did_last_launch_fail.setter
    def did_last_launch_fail(self, value: bool) -> None:
        self.__settings.setValue(self.KEY_DID_LAST_LAUNCH_FAIL, value)
