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

import json
from typing import Any, Dict, Optional

from qgis.core import QgsNetworkAccessManager
from qgis.PyQt.QtCore import QUrl, QUrlQuery
from qgis.PyQt.QtNetwork import (
    QNetworkReply,
    QNetworkRequest,
)

from nextgis_toolbox.core import utils
from nextgis_toolbox.core.qt_network_error import (
    QtNetworkError,
)
from nextgis_toolbox.nextgis_toolbox.sdk.authentication import (
    ToolboxAuthentication,
)
from nextgis_toolbox.nextgis_toolbox_plugin_interface import (
    NgToolboxPluginInterface,
)
from nextgis_toolbox.settings.nextgis_toolbox_plugin_settings import (
    NgToolboxPluginSettings,
)

API_BASE_ENDPOINT = "https://toolbox.nextgis.com/api"


class ToolboxApiClient:
    """Low-level HTTP client for NextGIS Toolbox API."""

    def __init__(self) -> None:
        """Initialize API client."""
        self._authentication = None

        NgToolboxPluginInterface.instance().settings_changed.connect(
            self.set_authentication
        )

        self.set_authentication()

    def set_authentication(self) -> None:
        """
        Set current authentication object.
        """
        settings = NgToolboxPluginSettings()
        token = settings.nextgis_toolbox_token

        if not token:
            self._authentication = None
            return

        authentication = ToolboxAuthentication(token)
        self._authentication = authentication

    def get(
        self,
        sub_url: str,
        params: Optional[Dict[str, Any]] = None,
        use_auth: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute GET request and return parsed JSON.

        :param sub_url: Relative API path.
        :param params: Optional query parameters.
        :param use_auth: Whether authorization is required.

        :returns: Parsed JSON response.
        """
        content = self.get_content(
            sub_url=sub_url,
            params=params,
            use_auth=use_auth,
        )

        return json.loads(content.decode("utf-8"))

    def get_content(
        self,
        sub_url: str,
        params: Optional[Dict[str, Any]] = None,
        use_auth: bool = False,
    ) -> bytes:
        """
        Execute GET request and return raw binary content.

        :param sub_url: Relative API path or full URL.
        :param params: Optional query parameters.
        :param use_auth: Whether authorization is required.

        :returns: Raw response content.
        """

        request = self._create_request(
            sub_url=sub_url,
            params=params,
            use_auth=use_auth,
        )

        response = QgsNetworkAccessManager.instance().blockingGet(request)

        self._validate_response(response)

        return response.content().data()

    def post(
        self,
        sub_url: str,
        payload: Dict[str, Any],
        use_auth: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute POST request with JSON payload.

        :param sub_url: Relative API path.
        :param payload: Request payload.
        :param use_auth: Whether authorization is required.

        :returns: Parsed JSON response.
        """

        request = self._create_request(
            sub_url=sub_url,
            use_auth=use_auth,
        )

        response = QgsNetworkAccessManager.instance().blockingPost(
            request,
            json.dumps(payload).encode("utf-8"),
        )

        self._validate_response(response)

        response_content = response.content().data().decode("utf-8")

        return json.loads(response_content)

    def _create_request(
        self,
        sub_url: str,
        params: Optional[Dict[str, Any]] = None,
        use_auth: bool = False,
    ) -> QNetworkRequest:
        """
        Create configured API request.

        :param sub_url: Relative API path.
        :param params: Optional query parameters.
        :param use_auth: Whether authorization is required.

        :returns: Configured request.
        """
        qurl = self._create_url(sub_url)
        qurl_query = QUrlQuery()

        params = {} if params is None else params
        for key, value in params.items():
            qurl_query.addQueryItem(str(key), str(value))

        qurl.setQuery(qurl_query)

        request = QNetworkRequest(qurl)

        request.setRawHeader(b"Content-Type", b"application/json")
        request.setRawHeader(
            b"Accept-Language",
            utils.qgis_locale().encode(),
        )

        if use_auth and self._authentication is not None:
            headers = self._authentication.get_headers()

            for header_name, header_value in headers.items():
                request.setRawHeader(
                    header_name.encode("utf-8"),
                    header_value.encode("utf-8"),
                )

        return request

    def _create_url(self, sub_url: str) -> QUrl:
        """Create URL for relative API path or absolute URL.

        :param sub_url: Relative API path or full URL.

        :returns: Qt URL instance.
        """
        qurl = QUrl(sub_url)
        if qurl.isValid() and not qurl.isRelative():
            return qurl

        return QUrl(f"{API_BASE_ENDPOINT}/{sub_url.lstrip('/')}")

    def _validate_response(
        self,
        response: QNetworkReply,
    ) -> None:
        """
        Validate Qt network response.

        :param response: Network response object.

        :raises ConnectionError: If request failed.
        """

        if response.error() == QNetworkReply.NetworkError.NoError:
            return

        error = QtNetworkError.from_qt(response.error())

        raise ConnectionError(
            error.value.code,
            error.value.description,
        )
