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

import json
from typing import Any, Dict, Optional

from qgis.core import (
    QgsFeedback,
    QgsNetworkAccessManager,
    QgsNetworkReplyContent,
)
from qgis.PyQt.QtCore import QObject, QUrl, QUrlQuery, pyqtSignal
from qgis.PyQt.QtNetwork import (
    QNetworkReply,
    QNetworkRequest,
)

from nextgis_toolbox.core import utils
from nextgis_toolbox.core.constants import DEFAULT_API_ENDPOINT
from nextgis_toolbox.core.qt_network_error import (
    QtNetworkError,
)
from nextgis_toolbox.nextgis_toolbox.sdk.authentication import (
    ToolboxAuthentication,
)


class ToolboxApiClient(QObject):
    """Low-level HTTP client for NextGIS Toolbox API."""

    endpoint_changed = pyqtSignal()
    authentication_changed = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QObject] = None,
        endpoint: Optional[str] = DEFAULT_API_ENDPOINT,
        authentication: Optional[ToolboxAuthentication] = None,
    ) -> None:
        """Initialize API client."""
        super().__init__(parent)
        self._endpoint = endpoint
        self._authentication = authentication

    @property
    def endpoint(self) -> Optional[str]:
        """Get current API endpoint URL."""
        return self._endpoint

    @endpoint.setter
    def endpoint(self, endpoint: str) -> None:
        """
        Set API endpoint URL.

        :param endpoint: Base URL for API requests.
        """
        self._endpoint = endpoint
        self.endpoint_changed.emit()

    @property
    def authentication(self) -> Optional[ToolboxAuthentication]:
        """Get current authentication object."""
        return self._authentication

    @authentication.setter
    def authentication(
        self, authentication: Optional[ToolboxAuthentication] = None
    ) -> None:
        """
        Set current authentication object.

        :param authentication: Authentication object to use.
        """
        self._authentication = authentication
        self.authentication_changed.emit()

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        feedback: Optional[QgsFeedback] = None,
    ) -> Dict[str, Any]:
        """
        Execute GET request and return parsed JSON.

        :param url: Relative API path.
        :param params: Optional query parameters.
        :param feedback: Optional feedback object for progress reporting.

        :returns: Parsed JSON response.
        """
        content = self.get_raw_data(
            url=url,
            url_params=params,
            feedback=feedback,
        )

        return json.loads(content.decode())

    def get_raw_data(
        self,
        url: str,
        url_params: Optional[Dict[str, Any]] = None,
        feedback: Optional[QgsFeedback] = None,
    ) -> bytes:
        """
        Execute GET request and return raw binary content.

        :param url: Relative API path or full URL.
        :param url_params: Optional query parameters.
        :param feedback: Optional feedback object for progress reporting.

        :returns: Raw response content.
        """

        request = self._create_request(url, url_params)

        response = QgsNetworkAccessManager.instance().blockingGet(
            request, feedback=feedback
        )
        if feedback is not None and feedback.isCanceled():
            raise ConnectionError(
                QNetworkReply.NetworkError.OperationCanceledError,
                "Request was canceled by user.",
            )

        self._validate_response(response)

        return response.content().data()

    def post(
        self,
        url: str,
        payload_object: Dict[str, Any],
        feedback: Optional[QgsFeedback] = None,
    ) -> Dict[str, Any]:
        """
        Execute POST request with JSON payload.

        :param url: Relative API path.
        :param payload: Request payload.
        :param use_auth: Whether authorization is required.
        :param feedback: Optional feedback object for progress reporting.

        :returns: Parsed JSON response.
        """

        request = self._create_request(url)
        data = json.dumps(payload_object).encode()

        response = QgsNetworkAccessManager.instance().blockingPost(
            request,
            data,
            feedback=feedback,
        )

        if feedback is not None and feedback.isCanceled():
            raise ConnectionError(
                QNetworkReply.NetworkError.OperationCanceledError,
                "Request was canceled by user.",
            )

        self._validate_response(response)

        response_content = response.content().data().decode("utf-8")

        return json.loads(response_content)

    def _create_request(
        self,
        url: str,
        url_params: Optional[Dict[str, Any]] = None,
        use_auth: bool = False,
    ) -> QNetworkRequest:
        """
        Create configured API request.

        :param sub_url: Relative API path.
        :param params: Optional query parameters.
        :param use_auth: Whether authorization is required.

        :returns: Configured request.
        """
        query_url_params = QUrlQuery()
        url_params = {} if url_params is None else url_params
        for key, value in url_params.items():
            query_url_params.addQueryItem(str(key), str(value))

        qurl = self._create_url(url)
        qurl.setQuery(query_url_params)

        request = QNetworkRequest(qurl)
        self._apply_headers(
            request,
            {
                "Content-Type": "application/json",
                "Accept-Language": utils.qgis_locale(),
            },
        )
        self._apply_authentication(request)

        return request

    def _create_url(self, sub_url: str) -> QUrl:
        """Create URL for relative API path or absolute URL.

        :param sub_url: Relative API path or full URL.

        :returns: Qt URL instance.
        """
        qurl = QUrl(sub_url)
        if qurl.isValid() and not qurl.isRelative():
            return qurl

        return QUrl(f"{self._endpoint.rstrip('/')}/api/{sub_url.lstrip('/')}")

    def _validate_response(
        self,
        response: QgsNetworkReplyContent,
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

    def _apply_headers(
        self, request: QNetworkRequest, headers: Dict[str, str]
    ) -> None:
        """
        Apply given headers to the request.

        :param request: Network request to apply headers to.
        :param headers: Dictionary of headers to apply.
        """
        for header_name, header_value in headers.items():
            request.setRawHeader(header_name.encode(), header_value.encode())

    def _apply_authentication(self, request: QNetworkRequest) -> None:
        """
        Apply current authentication to the given request.

        :param request: Network request to apply authentication to.
        """
        if self._authentication is not None:
            self._authentication.apply(request)
