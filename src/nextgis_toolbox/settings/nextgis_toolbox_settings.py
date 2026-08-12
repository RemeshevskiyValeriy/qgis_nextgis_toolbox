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

import os
from enum import Enum
from typing import Optional

from qgis.core import QgsSettings

from nextgis_toolbox.core.constants import (
    DEFAULT_API_ENDPOINT,
    PLUGIN_SETTINGS_GROUP,
)


class AuthenticationType(str, Enum):
    NONE = "none"
    TOKEN = "token"  # nosec B105

    def __str__(self) -> str:
        return self.value


class NextgisToolboxSettings:
    """Centralized settings handler for the NextGIS Toolbox."""

    ENV_API_ENDPOINT = "NEXTGIS_TOOLBOX_ENDPOINT"
    ENV_AUTHENTICATION_TYPE = "NEXTGIS_TOOLBOX_AUTHENTICATION_TYPE"
    ENV_AUTHENTICATION_TOKEN = "NEXTGIS_TOOLBOX_AUTHENTICATION_TOKEN"  # nosec B105

    KEY_API_ENDPOINT = f"{PLUGIN_SETTINGS_GROUP}/api/endpoint"
    KEY_AUTHENTICATION_TYPE = f"{PLUGIN_SETTINGS_GROUP}/authentication/type"
    KEY_AUTHENTICATION_TOKEN = f"{PLUGIN_SETTINGS_GROUP}/authentication/token"

    KEY_IS_DEBUG_LOGS_ENABLED = (
        f"{PLUGIN_SETTINGS_GROUP}/other/debugLogsEnabled"
    )
    KEY_IS_EXPERIMENTAL_QGIS_INTEGRATION_ENABLED = (
        f"{PLUGIN_SETTINGS_GROUP}/other/isExperimentalQgisIntegrationEnabled"
    )
    KEY_IS_DEVELOPER_MODE = f"{PLUGIN_SETTINGS_GROUP}/other/isDeveloperMode"
    KEY_DID_LAST_LAUNCH_FAIL = (
        f"{PLUGIN_SETTINGS_GROUP}/other/didLastLaunchFail"
    )

    DEFAULT_AUTHENTICATION_TYPE = AuthenticationType.TOKEN

    _settings: QgsSettings

    def __init__(self) -> None:
        self._settings = QgsSettings()

    @property
    def endpoint(self) -> str:
        """Return saved NextGIS Toolbox API endpoint."""
        env_endpoint = os.getenv(self.ENV_API_ENDPOINT, "").strip()
        if env_endpoint:
            return env_endpoint

        endpoint = self._settings.value(
            self.KEY_API_ENDPOINT,
            defaultValue=DEFAULT_API_ENDPOINT,
            type=str,
        ).strip()
        return endpoint or DEFAULT_API_ENDPOINT

    @endpoint.setter
    def endpoint(self, value: Optional[str]) -> None:
        endpoint = value.strip() if value else None
        self._settings.setValue(self.KEY_API_ENDPOINT, endpoint or None)

    @property
    def authentication_type(self) -> AuthenticationType:
        """Return saved NextGIS Toolbox authentication type."""
        env_authentication_type = os.getenv(
            self.ENV_AUTHENTICATION_TYPE,
            "",
        ).strip()
        if env_authentication_type:
            raw_authentication_type = env_authentication_type
        else:
            raw_authentication_type = self._settings.value(
                self.KEY_AUTHENTICATION_TYPE,
                defaultValue="",
                type=str,
            )

        authentication_type = None
        valid_values = {item.value for item in AuthenticationType}
        if raw_authentication_type in valid_values:
            authentication_type = AuthenticationType(raw_authentication_type)

        effective_authentication_type = (
            authentication_type or self.DEFAULT_AUTHENTICATION_TYPE
        )
        if (
            effective_authentication_type == AuthenticationType.NONE
            and self.authentication_token
        ):
            return AuthenticationType.TOKEN

        return effective_authentication_type

    @authentication_type.setter
    def authentication_type(self, value: AuthenticationType) -> None:
        self._settings.setValue(
            self.KEY_AUTHENTICATION_TYPE,
            str(value),
        )

    @property
    def real_authentication_type(self) -> AuthenticationType:
        """Return the effective authentication type, considering the presence of a token."""
        settings_type = self.authentication_type
        token = self.authentication_token
        if settings_type == AuthenticationType.TOKEN and not token:
            return AuthenticationType.NONE

        return settings_type

    @property
    def authentication_token(self) -> str:
        """Return saved NextGIS Toolbox token."""
        env_authentication_token = os.getenv(
            self.ENV_AUTHENTICATION_TOKEN,
            "",
        ).strip()
        if env_authentication_token:
            return env_authentication_token

        return self._settings.value(
            self.KEY_AUTHENTICATION_TOKEN,
            defaultValue="",
            type=str,
        ).strip()

    @authentication_token.setter
    def authentication_token(self, value: Optional[str]) -> None:
        token = value.strip() if value else None
        self._settings.setValue(
            self.KEY_AUTHENTICATION_TOKEN,
            token,
        )

    @property
    def cache_ttl_hours(self) -> int:
        """Return the configured cache TTL in hours."""
        return 24

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
    def is_experimental_qgis_integration_enabled(self) -> bool:
        """Check if experimental semantic-driven QGIS integration is enabled."""
        return self._settings.value(
            self.KEY_IS_EXPERIMENTAL_QGIS_INTEGRATION_ENABLED,
            defaultValue=False,
            type=bool,
        )

    @is_experimental_qgis_integration_enabled.setter
    def is_experimental_qgis_integration_enabled(self, value: bool) -> None:
        self._settings.setValue(
            self.KEY_IS_EXPERIMENTAL_QGIS_INTEGRATION_ENABLED,
            value,
        )

    @property
    def is_developer_mode(self) -> bool:
        """Check if developer-only tools are enabled."""
        return self._settings.value(
            self.KEY_IS_DEVELOPER_MODE,
            defaultValue=False,
            type=bool,
        )

    @is_developer_mode.setter
    def is_developer_mode(self, value: bool) -> None:
        self._settings.setValue(self.KEY_IS_DEVELOPER_MODE, value)

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
