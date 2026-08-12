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

import threading

from qgis.core import Qgis
from qgis.gui import QgsMessageBar
from qgis.PyQt import sip
from qgis.PyQt.QtWidgets import QApplication, QPushButton, QWidget

from nextgis_toolbox.notifier.message_bar_notifier import (
    MESSAGE_BAR_MESSAGE_ID_PROPERTY,
    MessageBarNotifier,
)


def test_message_bar_notifier_queues_messages_from_worker_thread(
    qgis_app,
) -> None:
    del qgis_app

    parent_widget = QWidget()
    message_bar = QgsMessageBar(parent_widget)
    notifier = MessageBarNotifier(message_bar)
    result = {}

    def display_message() -> None:
        result["message_id"] = notifier.display_message(
            "Background success",
            level=Qgis.MessageLevel.Success,
            widget_factories=[lambda: QPushButton("Action")],
        )

    worker = threading.Thread(target=display_message)
    worker.start()
    worker.join(timeout=5)

    QApplication.processEvents()
    QApplication.processEvents()

    items = message_bar.items()

    assert worker.is_alive() is False
    assert len(items) == 1
    assert (
        items[0].property(MESSAGE_BAR_MESSAGE_ID_PROPERTY)
        == result["message_id"]
    )
    assert [
        button.text() for button in items[0].findChildren(QPushButton)
    ] == ["Action"]


def test_message_bar_notifier_defers_same_thread_delivery(
    qgis_app,
) -> None:
    del qgis_app

    parent_widget = QWidget()
    message_bar = QgsMessageBar(parent_widget)
    notifier = MessageBarNotifier(message_bar)

    message_id = notifier.display_message("Deferred message")

    assert message_bar.items() == []

    QApplication.processEvents()
    QApplication.processEvents()

    items = message_bar.items()

    assert len(items) == 1
    assert items[0].property(MESSAGE_BAR_MESSAGE_ID_PROPERTY) == message_id


def test_message_bar_notifier_ignores_deleted_message_bar_on_dismiss(
    qgis_app,
) -> None:
    del qgis_app

    parent_widget = QWidget()
    message_bar = QgsMessageBar(parent_widget)
    notifier = MessageBarNotifier(message_bar)

    sip.delete(message_bar)

    notifier.dismiss_all()
