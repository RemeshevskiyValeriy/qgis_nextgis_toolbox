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

import re
import uuid
from collections import deque
from dataclasses import dataclass
from functools import partial
from math import ceil
from typing import (
    Callable,
    Deque,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from qgis.core import Qgis
from qgis.gui import QgsMessageBar, QgsMessageBarItem
from qgis.PyQt import sip
from qgis.PyQt.QtCore import QTimer, pyqtSignal, pyqtSlot
from qgis.PyQt.QtWidgets import (
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QTextBrowser,
    QWidget,
)

from nextgis_toolbox.core.constants import PLUGIN_NAME
from nextgis_toolbox.core.exceptions import (
    ToolboxError,
    ToolboxWarning,
)
from nextgis_toolbox.core.logging import logger, open_plugin_logs
from nextgis_toolbox.core.utils import assert_not_none
from nextgis_toolbox.notifier.notifier_interface import NotifierInterface

MESSAGE_BAR_ITEM_OBJECT_NAME = "NextgisToolboxMessageBarItem"
MESSAGE_BAR_MESSAGE_ID_PROPERTY = "NextgisToolboxMessageId"
MESSAGE_BAR_AUTO_EXPAND_PATCHED_PROPERTY = (
    "NextgisToolboxMessageBarAutoExpandPatched"
)
WidgetFactory = Callable[[], QWidget]


@dataclass(frozen=True)
class MessageDisplayRequest:
    message_id: str
    message: str
    header: Optional[str]
    level: Qgis.MessageLevel
    clear_previous: bool
    duration: int
    widgets: Tuple[QWidget, ...]
    widget_factories: Tuple[WidgetFactory, ...]


@dataclass(frozen=True)
class ExceptionDisplayRequest:
    error: Exception


@dataclass(frozen=True)
class MessageDismissRequest:
    message_id: str


@dataclass(frozen=True)
class DismissAllRequest:
    pass


QueuedRequest = Union[
    MessageDisplayRequest,
    ExceptionDisplayRequest,
    MessageDismissRequest,
    DismissAllRequest,
]


class MessageBarNotifier(NotifierInterface):
    """Notifier implementation for displaying messages and exceptions in QGIS.

    Provides methods to show messages and exceptions using QGIS message bar.
    """

    _request_received = pyqtSignal(object)

    def __init__(self, parent: QgsMessageBar, expanding: bool = False) -> None:
        """Initialize MessageBarNotifier with an optional parent QObject.

        :param parent: The parent QObject for this notifier.
        :param expanding: Whether to expand existing messages on initialization.
        """
        super().__init__(parent)
        self._message_bar = parent
        self._expanding = expanding
        self._pending_requests: Deque[QueuedRequest] = deque()
        self._flush_is_scheduled = False
        self._request_received.connect(self._enqueue_request)

        if expanding:
            self._connect_auto_expand()
            self._expand_existing_items()

    def __del__(self) -> None:
        """Dismiss all messages on object deletion."""
        if self._notifier_is_deleted():
            return

        if self._message_bar_or_none() is None:
            return

        try:
            self._dismiss_all_now()
        except RuntimeError:
            logger.exception("Failed to dismiss messages on notifier deletion")

    @property
    def message_bar(self) -> QgsMessageBar:
        """Return the QGIS message bar used by this notifier."""
        return self._message_bar

    def display_message(
        self,
        message: str,
        *,
        header: Optional[str] = None,
        level: Qgis.MessageLevel = Qgis.MessageLevel.Info,
        clear_previous: bool = False,
        widgets: Optional[List[QWidget]] = None,
        widget_factories: Optional[List[WidgetFactory]] = None,
        **kwargs,  # noqa: ANN003, ARG002
    ) -> str:
        """Display a message to the user via the QGIS message bar.

        :param message: The message to display.
        :param level: The message level as Qgis.MessageLevel.
        :param clear_previous: Whether to clear previous messages before displaying this one.
        :param widgets: Custom widgets for message.

        :return: An identifier for the displayed message.
        """
        message_id = str(uuid.uuid4())
        if self._notifier_is_deleted():
            return message_id

        message_bar = self._message_bar_or_none()
        if message_bar is None:
            return message_id

        request = MessageDisplayRequest(
            message_id=message_id,
            message=message,
            header=header,
            level=level,
            clear_previous=clear_previous,
            duration=kwargs.get(
                "duration",
                message_bar.defaultMessageTimeout(level),
            ),
            widgets=tuple(
                widget
                for widget in (widgets or [])
                if isinstance(widget, QWidget)
            ),
            widget_factories=tuple(widget_factories or []),
        )

        self._request_received.emit(request)

        return message_id

    def display_exception(self, error: Exception) -> str:
        """Display an exception as an error message to the user.

        :param error: The exception to display.

        :return: An identifier for the displayed message.
        """
        normalized_error = self._normalize_exception(error)
        if self._notifier_is_deleted():
            return normalized_error.error_id

        self._request_received.emit(ExceptionDisplayRequest(normalized_error))
        return normalized_error.error_id

    @pyqtSlot(object)
    def _enqueue_request(self, request: object) -> None:
        if not isinstance(
            request,
            (
                MessageDisplayRequest,
                ExceptionDisplayRequest,
                MessageDismissRequest,
                DismissAllRequest,
            ),
        ):
            return

        self._pending_requests.append(request)
        if self._flush_is_scheduled:
            return

        self._flush_is_scheduled = True
        QTimer.singleShot(0, self._flush_pending_requests)

    def _flush_pending_requests(self) -> None:
        self._flush_is_scheduled = False

        while self._pending_requests:
            request = self._pending_requests.popleft()
            if isinstance(request, MessageDisplayRequest):
                self._show_message_from_request(request)
                continue

            if isinstance(request, ExceptionDisplayRequest):
                self._show_exception(request.error)
                continue

            if isinstance(request, MessageDismissRequest):
                self._dismiss_message_now(request.message_id)
                continue

            self._dismiss_all_now()

    def _show_message_from_request(
        self,
        request: MessageDisplayRequest,
    ) -> None:
        message_bar = self._message_bar_or_none()
        if message_bar is None:
            return

        if request.clear_previous:
            self._dismiss_all_now()

        is_global_message_bar = (
            message_bar.parent().objectName() == "centralwidget"
        )
        header = request.header
        if not header and is_global_message_bar:
            header = PLUGIN_NAME

        widget = message_bar.createMessage(header, request.message)
        widget = assert_not_none(
            widget,
            "Failed to create QGIS message bar item",
        )

        item = assert_not_none(
            message_bar.pushWidget(widget, request.level, request.duration),
            "Failed to push QGIS message bar widget",
        )
        item.setObjectName(MESSAGE_BAR_ITEM_OBJECT_NAME)
        item.setProperty(
            MESSAGE_BAR_MESSAGE_ID_PROPERTY,
            request.message_id,
        )

        custom_widgets = self._materialize_widgets(
            request.widgets,
            request.widget_factories,
        )
        for custom_widget in custom_widgets:
            custom_widget.setParent(item)
            item.layout().addWidget(custom_widget)

        if self._expanding:
            self._expand_message_bar(item)

        logger.log(request.level, request.message)

    def _show_exception(self, error: Exception) -> str:
        error = self._normalize_exception(error)

        message = error.user_message.rstrip(".") + "."

        message_bar = self._message_bar_or_none()
        if message_bar is None:
            return error.error_id

        is_global_message_bar = (
            message_bar.parent().objectName() == "centralwidget"
        )
        header = PLUGIN_NAME if is_global_message_bar else None
        widget = message_bar.createMessage(header, message)
        widget = assert_not_none(
            widget,
            "Failed to create QGIS message bar item",
        )

        if not isinstance(error, Warning):
            self._add_error_buttons(error, widget)

        level = (
            Qgis.MessageLevel.Critical
            if not isinstance(error, ToolboxWarning)
            else Qgis.MessageLevel.Warning
        )

        item = assert_not_none(
            message_bar.pushWidget(widget, level),
            "Failed to push QGIS exception message bar widget",
        )
        item.setObjectName(MESSAGE_BAR_ITEM_OBJECT_NAME)
        item.setProperty(MESSAGE_BAR_MESSAGE_ID_PROPERTY, error.error_id)

        if self._expanding:
            self._expand_message_bar(item)

        if level == Qgis.MessageLevel.Critical:
            logger.exception(error.log_message, exc_info=error)
        else:
            logger.warning(error.user_message)

        return error.error_id

    def dismiss_message(self, message_id: str) -> None:
        """Dismiss a specific message by its identifier.

        :param message_id: The identifier of the message to dismiss.
        """
        if self._notifier_is_deleted():
            return

        self._request_received.emit(MessageDismissRequest(message_id))

    def _dismiss_message_now(self, message_id: str) -> None:
        message_bar = self._message_bar_or_none()
        if message_bar is None:
            return

        for notification in list(message_bar.items()):
            if (
                notification.objectName() != MESSAGE_BAR_ITEM_OBJECT_NAME
                or notification.property(MESSAGE_BAR_MESSAGE_ID_PROPERTY)
                != message_id
            ):
                continue
            message_bar.popWidget(notification)

    def dismiss_all(self) -> None:
        """Dismiss all currently displayed messages."""
        if self._notifier_is_deleted():
            return

        self._request_received.emit(DismissAllRequest())

    def _dismiss_all_now(self) -> None:
        message_bar = self._message_bar_or_none()
        if message_bar is None:
            return

        for notification in list(message_bar.items()):
            if notification.objectName() != MESSAGE_BAR_ITEM_OBJECT_NAME:
                continue
            message_bar.popWidget(notification)

    def _normalize_exception(
        self,
        error: Exception,
    ) -> Union[ToolboxError, ToolboxWarning]:
        if isinstance(error, (ToolboxError, ToolboxWarning)):
            return error

        old_error = error
        normalized_error = (
            ToolboxError()
            if not isinstance(error, Warning)
            else ToolboxWarning()
        )
        normalized_error.__cause__ = old_error
        return normalized_error

    def _message_bar_or_none(self) -> Optional[QgsMessageBar]:
        try:
            message_bar = self._message_bar
        except RuntimeError:
            return None

        if sip.isdeleted(message_bar):
            return None

        return message_bar

    def _notifier_is_deleted(self) -> bool:
        try:
            return sip.isdeleted(self)
        except RuntimeError:
            return True

    def _materialize_widgets(
        self,
        widgets: Sequence[QWidget],
        widget_factories: Sequence[WidgetFactory],
    ) -> List[QWidget]:
        if len(widget_factories) == 0:
            return self._widgets_in_message_bar_thread(widgets)

        materialized_widgets: List[QWidget] = []
        for widget_factory in widget_factories:
            try:
                widget = widget_factory()
            except Exception as error:
                logger.exception(
                    "Failed to create a message bar widget",
                    exc_info=error,
                )
                continue

            if isinstance(widget, QWidget):
                materialized_widgets.append(widget)

        return self._widgets_in_message_bar_thread(materialized_widgets)

    def _widgets_in_message_bar_thread(
        self,
        widgets: Sequence[QWidget],
    ) -> List[QWidget]:
        message_bar = self._message_bar_or_none()
        if message_bar is None:
            return []

        allowed_widgets: List[QWidget] = []
        for widget in widgets:
            if sip.isdeleted(widget):
                continue

            if widget.thread() != message_bar.thread():
                logger.warning(
                    "Message bar widgets must belong to the message bar "
                    "thread; use widget_factories to create them there"
                )
                continue

            allowed_widgets.append(widget)

        return allowed_widgets

    def _connect_auto_expand(self) -> None:
        message_bar = self._message_bar_or_none()
        if message_bar is None:
            return

        if message_bar.property(MESSAGE_BAR_AUTO_EXPAND_PATCHED_PROPERTY):
            return

        message_bar.widgetAdded.connect(self._expand_message_bar)
        message_bar.setProperty(
            MESSAGE_BAR_AUTO_EXPAND_PATCHED_PROPERTY,
            True,
        )

    def _expand_existing_items(self) -> None:
        message_bar = self._message_bar_or_none()
        if message_bar is None:
            return

        for item in list(message_bar.items()):
            self._expand_message_bar(item)

    def _expand_message_bar(self, item: QWidget) -> None:
        if not isinstance(item, QWidget):
            return

        QTimer.singleShot(
            0,
            partial(self._expand_message_bar_later, item),
        )

    def _expand_message_bar_later(self, item: QWidget) -> None:
        if not isinstance(item, QWidget):
            return

        message_bar = self._message_bar_or_none()
        if message_bar is None:
            return

        if item not in message_bar.items():
            return

        browser = item.findChild(QTextBrowser)
        if browser is None:
            return

        message_bar.setSizePolicy(
            message_bar.sizePolicy().horizontalPolicy(),
            QSizePolicy.Policy.Preferred,
        )

        text_height = browser.document().size().height()
        margins = browser.contentsMargins()
        max_margin = max(margins.top(), margins.bottom())
        browser.setContentsMargins(
            margins.left(), max_margin, margins.right(), max_margin
        )
        text_browser_height = ceil(text_height + 2 * max_margin)
        browser.setFixedHeight(text_browser_height)

    def _add_error_buttons(
        self, error: ToolboxError, item: QgsMessageBarItem
    ) -> None:
        def show_details() -> None:
            user_message = error.user_message.rstrip(".")
            user_message = re.sub(
                r"</?(i|b)\b[^>]*?>", "", user_message, flags=re.IGNORECASE
            )
            QMessageBox.information(
                self.message_bar, user_message, error.detail or ""
            )

        widget = item

        if error.try_again is not None:

            def try_again() -> None:
                error.try_again()
                self._message_bar.popWidget(item)

            button = QPushButton(self.tr("Try again"))
            button.pressed.connect(try_again)
            widget.layout().addWidget(button)

        for action_name, action_callback in error.actions:
            button = QPushButton(action_name)
            button.pressed.connect(action_callback)
            widget.layout().addWidget(button)

        if error.detail is not None:
            button = QPushButton(self.tr("Details"))
            button.pressed.connect(show_details)
            widget.layout().addWidget(button)
        else:
            button = QPushButton(self.tr("Open logs"))
            button.pressed.connect(open_plugin_logs)
            widget.layout().addWidget(button)

        if type(error) is ToolboxError:
            button = QPushButton(self.tr("Let us know"))
            button.pressed.connect(self.report_problem)
            widget.layout().addWidget(button)
