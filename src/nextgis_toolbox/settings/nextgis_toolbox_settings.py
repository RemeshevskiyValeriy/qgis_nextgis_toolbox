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

from enum import Enum
from typing import Optional

from qgis.core import QgsSettings

from nextgis_toolbox.core.constants import (
    DEFAULT_API_ENDPOINT,
    PLUGIN_SETTINGS_GROUP,
)


class AuthenticationType(str, Enum):
    NONE = "none"
    TOKEN = "token"

    def __str__(self) -> str:
        return self.value


class NextgisToolboxSettings:
    """Centralized settings handler for the NextGIS Toolbox."""

    KEY_API_ENDPOINT = f"{PLUGIN_SETTINGS_GROUP}/api/endpoint"
    KEY_AUTHENTICATION_TYPE = f"{PLUGIN_SETTINGS_GROUP}/authentication/type"
    KEY_AUTHENTICATION_TOKEN = f"{PLUGIN_SETTINGS_GROUP}/authentication/token"
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
    def endpoint(self) -> str:
        """Return saved NextGIS Toolbox API endpoint."""
        return self._settings.value(
            self.KEY_API_ENDPOINT,
            defaultValue=DEFAULT_API_ENDPOINT,
            type=str,
        )

    @endpoint.setter
    def endpoint(self, value: str) -> None:
        self._settings.setValue(
            self.KEY_API_ENDPOINT,
            value,
        )

    @property
    def authentication_type(self) -> AuthenticationType:
        """Return saved NextGIS Toolbox authentication type."""
        value = self._settings.value(
            self.KEY_AUTHENTICATION_TYPE,
            defaultValue=str(AuthenticationType.NONE),
            type=str,
        )
        return AuthenticationType(value)

    @authentication_type.setter
    def authentication_type(self, value: AuthenticationType) -> None:
        self._settings.setValue(
            self.KEY_AUTHENTICATION_TYPE,
            str(value),
        )

    @property
    def authentication_token(self) -> str:
        """Return saved NextGIS Toolbox token."""
        return self._settings.value(
            self.KEY_AUTHENTICATION_TOKEN,
            defaultValue="",
            type=str,
        )

    @authentication_token.setter
    def authentication_token(self, value: Optional[str]) -> None:
        if not value:
            self.authentication_type = AuthenticationType.NONE

        self._settings.setValue(
            self.KEY_AUTHENTICATION_TOKEN,
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
