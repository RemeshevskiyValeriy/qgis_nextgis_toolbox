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

from qgis.core import QgsSettings

from nextgis_toolbox.core.constants import PLUGIN_SETTINGS_GROUP


class NgToolboxPluginSettings:
    """Centralized settings handler for the NextGIS Toolbox Plugin."""

    KEY_NEXTGIS_TOOLBOX_TOKEN = (
        f"{PLUGIN_SETTINGS_GROUP}/authentication/nextgisToolboxToken"
    )
    KEY_IS_TOKEN_REMEMBERED = (
        f"{PLUGIN_SETTINGS_GROUP}/authentication/isTokenRemembered"
    )
    KEY_REFRESH_TASK_INTERVAL = (
        f"{PLUGIN_SETTINGS_GROUP}/tasks/refreshTaskInterval"
    )
    KEY_IS_DEBUG_LOGS_ENABLED = (
        f"{PLUGIN_SETTINGS_GROUP}/other/debugLogsEnabled"
    )
    KEY_DID_LAST_LAUNCH_FAIL = (
        f"{PLUGIN_SETTINGS_GROUP}/other/didLastLaunchFail"
    )

    _settings: QgsSettings

    def __init__(self) -> None:
        self._settings = QgsSettings()

    @property
    def nextgis_toolbox_token(self) -> str:
        """Return saved NextGIS Toolbox token."""
        return self._settings.value(
            self.KEY_NEXTGIS_TOOLBOX_TOKEN,
            defaultValue="",
            type=str,
        )

    @nextgis_toolbox_token.setter
    def nextgis_toolbox_token(self, value: str) -> None:
        self._settings.setValue(
            self.KEY_NEXTGIS_TOOLBOX_TOKEN,
            value,
        )

    @property
    def is_token_remembered(self) -> bool:
        """Check whether token saving is enabled."""
        return self._settings.value(
            self.KEY_IS_TOKEN_REMEMBERED,
            defaultValue=False,
            type=bool,
        )

    @is_token_remembered.setter
    def is_token_remembered(self, value: bool) -> None:
        self._settings.setValue(
            self.KEY_IS_TOKEN_REMEMBERED,
            value,
        )

    @property
    def refresh_task_interval(self) -> int:
        """Return task auto-refresh interval in seconds."""
        return self._settings.value(
            self.KEY_REFRESH_TASK_INTERVAL,
            defaultValue=0,
            type=int,
        )

    @refresh_task_interval.setter
    def refresh_task_interval(self, value: int) -> None:
        self._settings.setValue(
            self.KEY_REFRESH_TASK_INTERVAL,
            value,
        )

    @property
    def is_debug_logs_enabled(self) -> bool:
        """Check if debug logs are enabled."""
        return self._settings.value(
            self.KEY_IS_DEBUG_LOGS_ENABLED,
            defaultValue=True,
            type=bool,
        )

    @is_debug_logs_enabled.setter
    def is_debug_logs_enabled(self, value: bool) -> None:
        self._settings.setValue(self.KEY_IS_DEBUG_LOGS_ENABLED, value)

    @property
    def did_last_launch_fail(self) -> bool:
        """Checks whether the last plugin launch failed."""
        return self._settings.value(
            self.KEY_DID_LAST_LAUNCH_FAIL,
            defaultValue=False,
            type=bool,
        )

    @did_last_launch_fail.setter
    def did_last_launch_fail(self, value: bool) -> None:
        self._settings.setValue(self.KEY_DID_LAST_LAUNCH_FAIL, value)
