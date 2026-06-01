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

import sys
import uuid
from typing import Any, Callable, List, Optional, Tuple

from qgis.core import QgsApplication


class ToolboxExceptionInfoMixin:
    """Mixin providing common fields and logic for NextGIS Toolbox errors and warnings."""

    _error_id: str
    _log_message: str
    _user_message: str
    _detail: Optional[str]
    _try_again: Optional[Callable[[], Any]]
    _actions: List[Tuple[str, Callable[[], Any]]]

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize the exception info mixin.

        :param log_message: Log message for debugging.
        :param user_message: Message to display to the user.
        :param detail: Additional details about the error.
        """
        self._error_id = str(uuid.uuid4())

        default_message = QgsApplication.translate(
            "Exceptions", "An error occurred while running the plugin"
        )

        self._log_message = (
            log_message if log_message else default_message
        ).strip()

        self._user_message = (
            user_message if user_message else default_message
        ).strip()

        Exception.__init__(self, self._log_message)  # type: ignore reportArgumentType

        self.add_note("Message: " + self._user_message)

        self._detail = detail
        if self._detail is not None:
            self._detail = self._detail.strip()
            self.add_note("Details: " + self._detail)

        self._try_again = None

        self._actions = []

    @property
    def error_id(self) -> str:
        """Get the unique error identifier.

        :returns: Unique error ID as a string.
        """
        return self._error_id

    @property
    def log_message(self) -> str:
        """Get the log message for debugging.

        :returns: Log message.
        """
        return self._log_message

    @property
    def user_message(self) -> str:
        """Get the message intended for the user.

        :returns: User message.
        """
        return self._user_message

    @property
    def detail(self) -> Optional[str]:
        """Get additional details about the error.

        :returns: Error details or None.
        """
        return self._detail

    @property
    def try_again(self) -> Optional[Callable[[], Any]]:
        """Get the callable to retry the failed operation.

        :returns: Callable or None.
        """
        return self._try_again

    @try_again.setter
    def try_again(self, try_again: Optional[Callable[[], Any]]) -> None:
        """Set the callable to retry the failed operation.

        :param try_again: Callable to retry or None.
        """
        self._try_again = try_again

    @property
    def actions(self) -> List[Tuple[str, Callable[[], Any]]]:
        """Get the list of available actions for this exception.

        :returns: List of (action_name, action_callable) tuples.
        """
        return self._actions

    def add_action(self, name: str, callback: Callable[[], Any]) -> None:
        """Add an action to the exception.

        :param name: Name of the action.
        :param callback: Callable to execute for the action.
        """
        self._actions.append((name, callback))

    if sys.version_info < (3, 11):

        def add_note(self, note: str) -> None:
            """Add a note to the exception message (for Python < 3.11).

            :param note: Note string to add.

            :raises TypeError: If note is not a string.
            """
            if not isinstance(note, str):
                message = "Note must be a string"
                raise TypeError(message)
            message: str = self.args[0]
            self.args = (f"{message}\n{note}",)


class ToolboxError(ToolboxExceptionInfoMixin, Exception):
    """Base exception for errors in the NextGIS Toolbox.

    Inherit from this class to define custom error types for the plugin.
    """

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize the error.

        :param log_message: Log message for debugging.
        :param user_message: Message to display to the user.
        :param detail: Additional details about the error.
        """
        ToolboxExceptionInfoMixin.__init__(
            self,
            log_message,
            user_message=user_message,
            detail=detail,
        )
        Exception.__init__(self, self._log_message)


class ToolboxToolNotFoundError(ToolboxError):
    def __init__(
        self,
        *,
        tool_id: Optional[int] = None,
        name: Optional[str] = None,
    ) -> None:
        identifier = self._resolve_identifier(tool_id=tool_id, name=name)

        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "The Toolbox tool was not found."
        )
        # fmt: on

        super().__init__(
            log_message=f"Tool not found: {identifier}",
            user_message=default_message,
            detail=identifier,
        )

    def _resolve_identifier(
        self,
        *,
        tool_id: Optional[int],
        name: Optional[str],
    ) -> str:
        if tool_id is not None:
            return f"id={tool_id}"

        if name is not None:
            return f"name={name}"

        return "identifier is not provided"


class ToolboxTagNotFoundError(ToolboxError):
    def __init__(self, *, tag_id: Optional[int] = None) -> None:
        identifier = (
            f"id={tag_id}"
            if tag_id is not None
            else "identifier is not provided"
        )

        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "The Toolbox tag was not found."
        )
        # fmt: on

        super().__init__(
            log_message=f"Tag not found: {identifier}",
            user_message=default_message,
            detail=identifier,
        )


class ToolboxSortingError(ToolboxError):
    def __init__(self, entity_name: str, sort_by: Any) -> None:
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "Unsupported Toolbox sorting was requested."
        )
        # fmt: on

        super().__init__(
            log_message=(
                f"Unsupported {entity_name} sorting requested: {sort_by}"
            ),
            user_message=default_message,
            detail=f"entity={entity_name}, sort_by={sort_by}",
        )


class ToolboxWarning(ToolboxExceptionInfoMixin, UserWarning):
    """Base warning for non-critical issues in the NextGIS Toolbox.

    Inherit from this class to define custom warning types for the plugin.
    """

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize the warning.

        :param log_message: Log message for debugging.
        :param user_message: Message to display to the user.
        :param detail: Additional details about the error.
        """
        ToolboxExceptionInfoMixin.__init__(
            self,
            log_message,
            user_message=user_message,
            detail=detail,
        )
        Exception.__init__(self, self._log_message)


class ToolboxReloadAfterUpdateWarning(ToolboxWarning):
    """Warning raised when the plugin structure has changed after an update.

    This warning indicates that the plugin was successfully updated, but due to changes
    in its structure, it may fail to load properly until QGIS is restarted.
    """

    def __init__(self) -> None:
        """Initialize the warning."""
        # fmt: off
        super().__init__(
            log_message="Plugin structure changed",
            user_message=QgsApplication.translate(
                "Exceptions",
                "The plugin has been successfully updated. "
                "To continue working, please restart QGIS."
            ),
        )
        # fmt: on


class ToolboxUiLoadError(ToolboxError):
    """Exception raised when loading a UI file fails.

    :param log_message: Log message for debugging.
    :param user_message: Message to display to the user.
    :param detail: Additional details about the error.
    """

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize NextgisToolboxUiLoadError.

        :param log_message: Log message for debugging.
        :param user_message: Message to display to the user.
        :param detail: Additional details about the error.
        """
        default_message = QgsApplication.translate(
            "Exceptions", "Failed to load the user interface."
        )
        log_message = log_message if log_message else default_message
        user_message = user_message if user_message else default_message
        super().__init__(
            log_message=log_message,
            user_message=user_message,
            detail=detail,
        )


class ToolboxFileWriteError(ToolboxError):
    """Exception raised when writing a file fails."""

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize a file write error.

        :param log_message: Log message for debugging.
        :param user_message: Message to display to the user.
        :param detail: Additional details about the error.
        """
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "Failed to write the file."
        )
        # fmt: on

        super().__init__(
            log_message=log_message or default_message,
            user_message=user_message or default_message,
            detail=detail,
        )


class ToolboxCacheError(ToolboxError):
    """Exception raised when working with the local cache fails."""

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize a cache error."""
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "Failed to access the local cache."
        )
        # fmt: on

        super().__init__(
            log_message=log_message or default_message,
            user_message=user_message or default_message,
            detail=detail,
        )


class NextgisToolboxCacheReadError(ToolboxCacheError):
    """Exception raised when reading cached data fails."""

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize a cache read error."""
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "Failed to read the cached data."
        )
        # fmt: on

        super().__init__(
            log_message=log_message or default_message,
            user_message=user_message or default_message,
            detail=detail,
        )


class ToolboxCacheWriteError(ToolboxCacheError):
    """Exception raised when writing cached data fails."""

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize a cache write error."""
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "Failed to write the cached data."
        )
        # fmt: on

        super().__init__(
            log_message=log_message or default_message,
            user_message=user_message or default_message,
            detail=detail,
        )


class ToolboxCacheFormatError(ToolboxCacheError):
    """Exception raised when cached data has an unsupported format."""

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize a cache format error."""
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "Cached data has an unsupported format."
        )
        # fmt: on

        super().__init__(
            log_message=log_message or default_message,
            user_message=user_message or default_message,
            detail=detail,
        )


class ToolboxNetworkError(ToolboxError):
    """Exception raised when a network request fails."""

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize a network error.

        :param log_message: Log message for debugging.
        :param user_message: Message to display to the user.
        :param detail: Additional details about the error.
        """
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "Failed to complete the network request."
        )
        # fmt: on

        super().__init__(
            log_message=log_message or default_message,
            user_message=user_message or default_message,
            detail=detail,
        )


class ToolboxAuthenticationError(ToolboxNetworkError):
    """Exception raised when API authentication fails."""

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize an authentication error.

        :param log_message: Log message for debugging.
        :param user_message: Message to display to the user.
        :param detail: Additional details about the error.
        """
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "Authentication failed. Check the Toolbox API Key."
        )
        # fmt: on

        super().__init__(
            log_message=log_message or default_message,
            user_message=user_message or default_message,
            detail=detail,
        )


class ToolboxRequestCanceledError(ToolboxNetworkError):
    """Exception raised when a network request is canceled."""

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize a request cancellation error.

        :param log_message: Log message for debugging.
        :param user_message: Message to display to the user.
        :param detail: Additional details about the error.
        """
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "The request was canceled."
        )
        # fmt: on

        super().__init__(
            log_message=log_message or default_message,
            user_message=user_message or default_message,
            detail=detail,
        )


class ToolboxTaskExecutionError(ToolboxError):
    """Exception raised when a Toolbox task cannot be executed."""

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize a task execution error.

        :param log_message: Log message for debugging.
        :param user_message: Message to display to the user.
        :param detail: Additional details about the error.
        """
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "Failed to execute the Toolbox task."
        )
        # fmt: on

        super().__init__(
            log_message=log_message or default_message,
            user_message=user_message or default_message,
            detail=detail,
        )


class ToolboxFileUploadError(ToolboxTaskExecutionError):
    """Exception raised when an input file upload fails."""

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize a file upload error.

        :param log_message: Log message for debugging.
        :param user_message: Message to display to the user.
        :param detail: Additional details about the error.
        """
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "Failed to upload the input file."
        )
        # fmt: on

        super().__init__(
            log_message=log_message or default_message,
            user_message=user_message or default_message,
            detail=detail,
        )


class ToolboxTaskFailedError(ToolboxTaskExecutionError):
    """Exception raised when a Toolbox task finishes with an error."""

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize a task failure error.

        :param log_message: Log message for debugging.
        :param user_message: Message to display to the user.
        :param detail: Additional details about the error.
        """
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "The Toolbox task failed."
        )
        # fmt: on

        super().__init__(
            log_message=log_message or default_message,
            user_message=user_message or default_message,
            detail=detail,
        )


class ToolboxTaskTimeoutError(ToolboxTaskExecutionError):
    """Exception raised when waiting for a Toolbox task times out."""

    def __init__(
        self,
        log_message: Optional[str] = None,
        *,
        user_message: Optional[str] = None,
        detail: Optional[str] = None,
    ) -> None:
        """Initialize a task timeout error.

        :param log_message: Log message for debugging.
        :param user_message: Message to display to the user.
        :param detail: Additional details about the error.
        """
        # fmt: off
        default_message = QgsApplication.translate(
            "Exceptions",
            "Waiting for the Toolbox task timed out."
        )
        # fmt: on

        super().__init__(
            log_message=log_message or default_message,
            user_message=user_message or default_message,
            detail=detail,
        )


class ToolboxProcessingRequiredWarning(ToolboxWarning):
    """Warning shown when the Processing core plugin is disabled."""

    def __init__(self) -> None:
        """Initialize the warning."""
        # fmt: off
        super().__init__(
            log_message="Processing plugin is disabled",
            user_message=QgsApplication.translate(
                "Exceptions",
                "NextGIS Toolbox requires the QGIS core "
                'plugin "Processing" to be enabled. '
                "Please enable the Processing plugin in Plugin Manager "
                "and restart QGIS."
            ),
        )
        # fmt: on
