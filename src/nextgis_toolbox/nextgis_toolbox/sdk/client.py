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
from pathlib import Path
from typing import Any, Dict, Optional

from qgis.core import (
    QgsFeedback,
    QgsNetworkAccessManager,
)
from qgis.PyQt.QtCore import (
    QEventLoop,
    QIODevice,
    QObject,
    QSaveFile,
    QUrl,
    QUrlQuery,
    pyqtSignal,
)
from qgis.PyQt.QtNetwork import (
    QNetworkReply,
    QNetworkRequest,
)

from nextgis_toolbox.core import utils
from nextgis_toolbox.core.constants import DEFAULT_API_ENDPOINT
from nextgis_toolbox.core.exceptions import (
    NextgisToolboxAuthenticationError,
    NextgisToolboxNetworkError,
    NextgisToolboxRequestCanceledError,
)
from nextgis_toolbox.core.qt_network_error import (
    QtNetworkError,
)
from nextgis_toolbox.nextgis_toolbox.sdk.authentication import (
    ToolboxAuthentication,
)
from nextgis_toolbox.settings.nextgis_toolbox_settings import (
    AuthenticationType,
)


class ToolboxApiClient(QObject):
    """Low-level HTTP client for NextGIS Toolbox API."""

    endpoint_changed = pyqtSignal()
    authentication_changed = pyqtSignal()

    def __init__(
        self,
        parent: Optional[QObject] = None,
        endpoint: str = DEFAULT_API_ENDPOINT,
        authentication: Optional[ToolboxAuthentication] = None,
    ) -> None:
        """Initialize API client."""
        super().__init__(parent)
        self._endpoint = endpoint
        self._authentication = authentication

    @property
    def endpoint(self) -> str:
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
    def authentication_type(self) -> AuthenticationType:
        """Get current authentication type."""
        if self._authentication is None:
            return AuthenticationType.NONE

        return self._authentication.TYPE

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
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
        feedback: Optional[QgsFeedback] = None,
    ) -> Dict[str, Any]:
        """
        Execute GET request and return parsed JSON.

        :param path: Relative API path or absolute URL.
        :param query_params: Optional query parameters.
        :param feedback: Optional feedback object for progress reporting.

        :returns: Parsed JSON response.
        """
        response_bytes = self.get_bytes(
            path=path,
            query_params=query_params,
            feedback=feedback,
        )

        return json.loads(response_bytes.decode())

    def get_bytes(
        self,
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
        feedback: Optional[QgsFeedback] = None,
    ) -> bytes:
        """
        Execute GET request and return raw binary content.

        :param path: Relative API path or absolute URL.
        :param query_params: Optional query parameters.
        :param feedback: Optional feedback object for progress reporting.

        :returns: Raw response content.
        """
        request = self._build_request(path, query_params)

        response = QgsNetworkAccessManager.instance().blockingGet(
            request, feedback=feedback
        )

        self._raise_if_request_canceled(feedback)
        self._raise_for_network_error(response.error())

        return response.content().data()

    def download(
        self,
        path: str,
        destination_path: Path,
        query_params: Optional[Dict[str, Any]] = None,
        feedback: Optional[QgsFeedback] = None,
    ) -> Path:
        """Download response content directly to the destination path.

        :param path: Relative API path or absolute URL.
        :param destination_path: Target file path.
        :param query_params: Optional query parameters.
        :param feedback: Optional feedback object for progress reporting.

        :returns: Saved file path.
        """
        request = self._build_request(path, query_params)
        saved_path = Path(destination_path)
        saved_path.parent.mkdir(parents=True, exist_ok=True)

        output_file = QSaveFile(str(saved_path))
        if not output_file.open(QIODevice.OpenModeFlag.WriteOnly):
            raise OSError(f"Failed to open '{saved_path}' for writing.")

        reply = QgsNetworkAccessManager.instance().get(request)
        event_loop = QEventLoop(self)
        write_error: Optional[Exception] = None

        def write_available_data() -> None:
            nonlocal write_error

            if write_error is not None:
                return

            chunk = reply.readAll()
            if chunk.isEmpty():
                return

            chunk_bytes = chunk.data()
            written_bytes = output_file.write(chunk_bytes)

            if written_bytes != len(chunk_bytes):
                write_error = OSError(
                    f"Failed to write downloaded data to '{saved_path}'."
                )
                reply.abort()

        if feedback is not None:
            feedback.canceled.connect(reply.abort)

        reply.readyRead.connect(write_available_data)
        reply.finished.connect(write_available_data)
        reply.finished.connect(event_loop.quit)

        try:
            event_loop.exec()

            if write_error is not None:
                raise write_error

            self._raise_if_request_canceled(feedback)
            self._raise_for_network_error(reply.error())

            if not output_file.commit():
                raise OSError(
                    f"Failed to save downloaded file to '{saved_path}'."
                )
        except Exception:
            output_file.cancelWriting()
            raise
        finally:
            reply.deleteLater()

        return saved_path

    def post(
        self,
        path: str,
        payload: Dict[str, Any],
        feedback: Optional[QgsFeedback] = None,
    ) -> Dict[str, Any]:
        """
        Execute POST request with JSON payload.

        :param path: Relative API path or absolute URL.
        :param payload: Request payload.
        :param feedback: Optional feedback object for progress reporting.

        :returns: Parsed JSON response.
        """
        request = self._build_request(path)
        payload_bytes = json.dumps(payload).encode()

        response = QgsNetworkAccessManager.instance().blockingPost(
            request,
            payload_bytes,
            feedback=feedback,
        )

        self._raise_if_request_canceled(feedback)
        self._raise_for_network_error(response.error())

        response_content = response.content().data().decode()

        return json.loads(response_content)

    def _build_request(
        self,
        path: str,
        query_params: Optional[Dict[str, Any]] = None,
    ) -> QNetworkRequest:
        """
        Create configured API request.

        :param path: Relative API path or absolute URL.
        :param query_params: Optional query parameters.

        :returns: Configured request.
        """
        query_url_params = QUrlQuery()
        query_params = {} if query_params is None else query_params
        for key, value in query_params.items():
            query_url_params.addQueryItem(str(key), str(value))

        qurl = self._build_url(path)
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

    def _build_url(self, path: str) -> QUrl:
        """Create URL for relative API path or absolute URL.

        :param path: Relative API path or absolute URL.

        :returns: Qt URL instance.
        """
        qurl = QUrl(path)
        if qurl.isValid() and not qurl.isRelative():
            return qurl

        return QUrl(f"{self._endpoint.rstrip('/')}/api/{path.lstrip('/')}")

    def _raise_if_request_canceled(
        self,
        feedback: Optional[QgsFeedback],
    ) -> None:
        """Raise an exception if the request was canceled by the user."""
        if feedback is None or not feedback.isCanceled():
            return

        raise NextgisToolboxRequestCanceledError(
            log_message="Network request was canceled by user",
        )

    def _raise_for_network_error(
        self,
        network_error: QNetworkReply.NetworkError,
    ) -> None:
        """Raise a typed exception for a Qt network error."""
        if network_error == QNetworkReply.NetworkError.NoError:
            return

        detail = self._describe_network_error(network_error)

        if network_error in (
            QNetworkReply.NetworkError.AuthenticationRequiredError,
            QNetworkReply.NetworkError.ProxyAuthenticationRequiredError,
        ):
            raise NextgisToolboxAuthenticationError(
                log_message="Toolbox API authentication failed",
                detail=detail,
            )

        if network_error == QNetworkReply.NetworkError.OperationCanceledError:
            raise NextgisToolboxRequestCanceledError(
                log_message="Network request was canceled",
                detail=detail,
            )

        raise NextgisToolboxNetworkError(
            log_message="Network request failed",
            detail=detail,
        )

    def _describe_network_error(
        self,
        network_error: QNetworkReply.NetworkError,
    ) -> str:
        """Return a human-readable description for a Qt network error."""
        error = QtNetworkError.from_qt(network_error)

        if error is None:
            return f"Qt network error code: {network_error}"

        return f"{error.value.constant}: {error.value.description}"

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
