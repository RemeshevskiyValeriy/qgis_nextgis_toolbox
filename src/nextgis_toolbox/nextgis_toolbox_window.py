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
import os
import traceback
from time import sleep

from qgis.core import Qgis, QgsApplication, QgsMessageLog, QgsTask
from qgis.PyQt.QtCore import QObject, Qt, QThread, pyqtSignal
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QApplication,
    QDockWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QTableWidgetItem,
    QTableWidgetSelectionRange,
    QTreeWidgetItem,
)
from qgis.PyQt.uic import loadUiType

from nextgis_toolbox.inputs_dialog import InputsDialog
from nextgis_toolbox.nextgis_toolbox.tasks.models import ToolboxResult
from nextgis_toolbox.nextgis_toolbox_plugin_interface import (
    NgToolboxPluginInterface,
)

# from nextgis_toolbox.nextgis_toolbox_plugin_provider import NgPluginProvider
from nextgis_toolbox.results_dialog import ResultsDialog

PLUGIN_DIR = os.path.dirname(__file__)

MAIN_FORM_CLASS, _ = loadUiType(
    os.path.join(PLUGIN_DIR, "ui/nextgis_toolbox_window.ui")
)

USER_DATA_JSON = os.path.join(PLUGIN_DIR, "user_data.json")
if not os.path.exists(USER_DATA_JSON):
    with open(USER_DATA_JSON, "w+") as f:
        f.write('{"token": null, "history": [], "refresh": 0}')


class AutorefreshTasks(QObject):
    need_update = pyqtSignal()

    def __init__(self, interval):
        super().__init__()
        self.interval = interval
        self.canceled = False

    def run(self):
        while not self.canceled:
            sleep(self.interval)
            self.need_update.emit()

    def cancel(self):
        self.canceled = True


class ToolboxDockWidget(QDockWidget):
    window_closed = pyqtSignal()

    def __init__(self, iface, parent=None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("NextGIS Toolbox"))
        self.inner_control = NgToolboxWindow(iface, self)
        self.inner_control.setWindowFlags(Qt.Widget)
        self.setWidget(self.inner_control)

    def close(self):
        self.inner_control.close()
        super().close()

    def closeEvent(self, event):
        self.window_closed.emit()

    def unload_proc(self):
        self.inner_control.remove_processing()


class NgToolboxWindow(QMainWindow, MAIN_FORM_CLASS):
    waited_tasks = {}
    provider = None

    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.iface = iface

        progressMessageBar = iface.messageBar().createMessage(
            self.tr("Loading Toolbox...")
        )
        progress = QProgressBar()
        progress.setMaximum(0)
        progress.setMinimum(0)
        progress.setValue(0)
        progressMessageBar.layout().addWidget(progress)
        iface.messageBar().pushWidget(progressMessageBar, Qgis.Info)
        QApplication.processEvents()
        try:
            plugin = NgToolboxPluginInterface.instance()
            tools_manager = plugin.tools_manager

            self.toolbox = tools_manager
        except Exception:
            self.iface.messageBar().pushMessage(
                "NextGis Toolbox",
                self.tr("Connection error!"),
                level=Qgis.Critical,
            )
            raise
        iface.messageBar().clearWidgets()

        with open(USER_DATA_JSON) as f:
            self.user_data = json.load(f)
        if self.user_data["token"]:
            self.tokenEdit.setText(self.user_data["token"])
            self.saveTokenCheckBox.setChecked(True)
            self.set_token(first_run=True)

        self.refresh_thread = None
        self.refresh_task = None
        self.refreshSpinBox.setValue(self.user_data["refresh"])
        self.set_auto_refresh(self.user_data["refresh"])

        self.create_tree()
        self.tableWidget.setColumnHidden(3, True)
        self.tableWidget.setSelectionBehavior(1)
        self.tabWidget.setCurrentIndex(0)

        self.treeWidget.itemDoubleClicked.connect(self.send_task)
        self.treeWidget.itemSelectionChanged.connect(self.show_what_this)
        self.treeFilter.textChanged.connect(self.create_tree)
        self.setTokenButton.clicked.connect(self.set_token)
        self.saveTokenCheckBox.clicked.connect(self.save_user_data)
        self.refreshSpinBox.valueChanged.connect(self.set_auto_refresh)
        self.tableWidget.itemSelectionChanged.connect(
            self.block_results_button
        )
        self.refreshButton.clicked.connect(self.refresh_orders_table)
        self.resultsButton.clicked.connect(self.show_results)
        self.infoButton.clicked.connect(self.show_info)

    def close(self):
        if self.refresh_task and not self.refresh_task.canceled:
            self.refresh_task.cancel()
            self.refresh_task = None
        if self.refresh_thread:
            if self.refresh_thread.isRunning():
                self.refresh_thread.quit()
            self.refresh_thread = None

    def create_tree(self, filter=None):
        self.treeWidget.clear()
        self.treeWidget.setColumnCount(2)
        self.treeWidget.hideColumn(1)
        self.treeWidget.sortByColumn(1, Qt.AscendingOrder)

        def add_item(tag_name, tag_tools, hidden_name=None):
            item = QTreeWidgetItem()
            item.setText(0, tag_name)
            # dirty trick for sorting
            if not hidden_name:
                hidden_name = tag_name
            item.setText(1, hidden_name)
            for tool in self.toolbox.tools():
                if (
                    tool.is_dev
                    or tool.id not in tag_tools
                    or (filter and filter.lower() not in tool.name.lower())
                ):
                    continue
                toolItem = QTreeWidgetItem(item)
                toolItem.setText(0, tool.name)
                toolItem.setText(1, tool.name)
                toolItem.setData(0, 100, tool.id)
                toolItem.setWhatsThis(0, tool.description)
            if not item.childCount():
                del item
            else:
                self.treeWidget.addTopLevelItem(item)

        add_item(
            self.tr("All"), [tool.id for tool in self.toolbox.tools()], "!!"
        )  # here it is !!
        if self.user_data["history"]:
            add_item(
                self.tr("Favorites"), self.user_data["history"], "!"
            )  # and here !

        for tag in self.toolbox.tags():
            add_item(tag.alias, tag.tools)
        if filter:
            self.treeWidget.expandAll()

    def init_processing(self):
        progressMessageBar = self.iface.messageBar().createMessage(
            self.tr("Loading processing algorithms...")
        )
        progress = QProgressBar()
        progress.setMaximum(0)
        progress.setMinimum(0)
        progress.setValue(0)
        progressMessageBar.layout().addWidget(progress)
        self.iface.messageBar().pushWidget(progressMessageBar, Qgis.Info)
        QApplication.processEvents()
        # self.provider = NgPluginProvider(self.toolbox)
        # QgsApplication.processingRegistry().addProvider(self.provider)
        self.iface.messageBar().clearWidgets()

    def remove_processing(self):
        # if self.provider:
        #     QgsApplication.processingRegistry().removeProvider(self.provider)
        # self.provider = None
        pass

    def set_token(self, first_run=False):
        token = self.tokenEdit.text()
        try:
            self.remove_processing()
            self.toolbox.set_current_user(token)
            self.tokenEdit.setStyleSheet("background: transparent;")
            if not first_run:
                QMessageBox.about(
                    self, None, self.tr("The token is correct. User changed.")
                )
        except Exception:
            self.toolbox.unset_current_user()
            self.iface.messageBar().pushMessage(
                "NextGis Toolbox",
                self.tr("Connection error!"),
                level=Qgis.Critical,
            )
            self.refreshButton.setEnabled(False)
            self.tableWidget.setRowCount(0)
            self.tableWidget.clearContents()
        except ValueError:
            self.toolbox.unset_current_user()
            self.tokenEdit.setStyleSheet("background: red;")
            QMessageBox.about(self, None, self.tr("Bad token!"))
            self.refreshButton.setEnabled(False)
            self.tableWidget.setRowCount(0)
            self.tableWidget.clearContents()
        else:
            self.build_orders_table()
            self.refreshButton.setEnabled(True)
            self.init_processing()
        finally:
            self.save_user_data(self.saveTokenCheckBox.isChecked())

    def save_user_data(self, checked):
        if checked and self.toolbox.token:
            self.user_data["token"] = self.tokenEdit.text()
        else:
            self.user_data["token"] = None
        with open(USER_DATA_JSON, "w") as f:
            json.dump(self.user_data, f)

    def build_orders_table(self):
        self.tableWidget.setRowCount(0)
        self.tableWidget.clearContents()
        orders = self.toolbox.orders_man.orders
        self.tableWidget.setRowCount(len(orders))
        for row, order in enumerate(orders):
            tool_name = [
                tool["name"]
                for tool in self.toolbox.tools
                if order.parameters.operation_name == tool["operation_id"]
            ]
            if not tool_name:
                continue
            tool_name = tool_name[0]
            nameItem = QTableWidgetItem(tool_name)
            nameItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            dateItem = QTableWidgetItem(str(order.created_at))
            dateItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            statusItem = QTableWidgetItem(str(order.status))
            if order.status == "SUCCESS":
                statusItem.setBackground(QColor(0, 255, 0))
            elif order.status == "FAILED":
                statusItem.setBackground(QColor(255, 0, 0))
            statusItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            orderIdItem = QTableWidgetItem(str(order.guid))

            self.tableWidget.setItem(row, 0, nameItem)
            self.tableWidget.setItem(row, 1, dateItem)
            self.tableWidget.setItem(row, 2, statusItem)
            self.tableWidget.setItem(row, 3, orderIdItem)

    def refresh_orders_table(self):
        if not self.toolbox.token:
            return
        if not self.isVisible():
            return
        try:
            self.toolbox.refresh_orders()
        except Exception:
            self.iface.messageBar().pushMessage(
                "NextGis Toolbox",
                self.tr("Connection error!"),
                level=Qgis.Critical,
            )
            return
        selection = self.tableWidget.selectedRanges()
        if selection:
            selection = QTableWidgetSelectionRange(
                selection[0].topRow(),
                selection[0].leftColumn(),
                selection[0].bottomRow(),
                selection[0].rightColumn(),
            )
        self.build_orders_table()
        if selection:
            self.tableWidget.setRangeSelected(selection, True)
            self.tableWidget.setCurrentCell(selection.topRow(), 0)
            self.block_results_button()

    def set_auto_refresh(self, interval):
        if self.refresh_task:
            if not self.refresh_task.canceled:
                self.refresh_task.cancel()
            self.refresh_task = None
        if self.refresh_thread:
            if self.refresh_thread.isRunning():
                self.refresh_thread.quit()
            self.refresh_thread = None
        self.user_data["refresh"] = interval
        self.save_user_data(self.saveTokenCheckBox.isChecked())
        if not interval:
            return
        self.refresh_task = AutorefreshTasks(interval)
        self.refresh_task.need_update.connect(self.refresh_orders_table)
        self.refresh_thread = QThread(self)
        self.refresh_task.moveToThread(self.refresh_thread)
        self.refresh_thread.started.connect(self.refresh_task.run)
        self.refresh_thread.start()

    def block_results_button(self):
        selection_model = self.tableWidget.selectionModel()
        row = self.tableWidget.currentRow()
        if len(selection_model.selectedRows()) != 1 or row < 0:
            self.resultsButton.setEnabled(False)
            self.infoButton.setEnabled(False)
        else:
            if self.tableWidget.item(row, 2).text() == "SUCCESS":
                self.resultsButton.setEnabled(True)
                self.infoButton.setEnabled(False)
            elif self.tableWidget.item(row, 2).text() == "FAILED":
                self.resultsButton.setEnabled(False)
                self.infoButton.setEnabled(True)
            else:
                self.resultsButton.setEnabled(False)
                self.infoButton.setEnabled(False)

    def show_what_this(self):
        selection = self.treeWidget.selectedItems()
        if len(selection) != 1:
            self.itemDescription.clear()
            return
        item = selection[0]
        if item.childCount() > 0:
            self.itemDescription.clear()
        else:
            self.itemDescription.clear()
            self.itemDescription.append(item.whatsThis(0))

    def waiting_detached(self, task, task_id):
        status = None
        try:
            while not task.isCanceled():
                try:
                    resp = self.toolbox.orders_man.get_status(task_id)
                except Exception:
                    self.iface.messageBar().pushMessage(
                        "NextGis Toolbox",
                        self.tr("Connection error!"),
                        level=Qgis.Critical,
                    )
                    raise
                status = resp["state"]
                if status == "SUCCESS":
                    return ToolboxResult("", "", resp["output"])
                elif status == "FAILED":
                    QMessageBox.about(
                        self, None, f"Order error: {resp['error']}"
                    )
                    break
                sleep(5)
        except Exception:
            err = traceback.format_exc()
            QMessageBox.about(self, None, self.tr("Error waiting results."))
            QgsMessageLog.logMessage(err, "NgToolbox", level=Qgis.Warning)
        del self.waited_tasks[task_id]

    def _send_task(self):
        print("accepted!")
        if self.inputs_dialog.wait_res:
            task = QgsTask.fromFunction(
                f"NextGis Toolbox: {self.inputs_dialog.task_id}",
                self.waiting_detached,
                on_finished=self.show_results_,
                task_id=self.inputs_dialog.task_id,
            )
            QgsApplication.taskManager().addTask(task)
            self.waited_tasks[self.inputs_dialog.task_id] = task
        self.refresh_orders_table()
        tool_inx = [
            tool["id"]
            for tool in self.toolbox.tools
            if tool["operation_id"] == self.current_tool_id
        ][0]
        if tool_inx not in self.user_data["history"]:
            self.user_data["history"].append(tool_inx)
            while len(self.user_data["history"]) > 10:
                del self.user_data["history"][0]
            self.create_tree(filter=self.treeFilter.text())
            self.save_user_data(self.saveTokenCheckBox.isChecked())

    def send_task(self, item, column):
        if not self.toolbox.token:
            QMessageBox.about(
                self, None, self.tr("Please, set the token first.")
            )
            self.tabWidget.setCurrentIndex(2)
            return
        if item.childCount() > 0:
            return

        self.current_tool_id = item.data(column, 100)
        tool_name = item.text(column)
        try:
            tool_inputs = self.toolbox.get_tool_inputs(
                tool_id=self.current_tool_id
            )
        except Exception:
            self.iface.messageBar().pushMessage(
                "NextGis Toolbox",
                self.tr("Connection error!"),
                level=Qgis.Critical,
            )
            return

        self.inputs_dialog = InputsDialog(
            self.current_tool_id, tool_name, tool_inputs, self.toolbox
        )
        self.inputs_dialog.accepted.connect(self._send_task)
        # accept = inputs_dialog.exec()
        self.inputs_dialog.show()

    def show_results(self):
        row = self.tableWidget.currentRow()
        order_id = self.tableWidget.item(row, 3).text()
        try:
            status = self.toolbox.orders_man.get_status(order_id)
        except Exception:
            self.iface.messageBar().pushMessage(
                "NextGis Toolbox",
                self.tr("Connection error!"),
                level=Qgis.Critical,
            )
            return
        results_dialog = ResultsDialog(
            ToolboxResult("", "", status["output"]), self.toolbox
        )
        results_dialog.exec()

    def show_results_(self, exception, result=None):
        """Show results after waiting_detached"""
        if exception is None:
            if result:
                results_dialog = ResultsDialog(result, self.toolbox)
                results_dialog.exec()
            self.iface.messageBar().pushMessage(
                "NextGis Toolbox", self.tr("Task completed"), level=Qgis.Info
            )
        else:
            self.iface.messageBar().pushMessage(
                "NextGis Toolbox", self.tr("Task failed!"), level=Qgis.Critical
            )
            raise exception

    def show_info(self):
        row = self.tableWidget.currentRow()
        order_id = self.tableWidget.item(row, 3).text()
        try:
            status = self.toolbox.orders_man.get_status(order_id)
        except Exception:
            self.iface.messageBar().pushMessage(
                "NextGis Toolbox",
                self.tr("Connection error!"),
                level=Qgis.Critical,
            )
            return
        QMessageBox.about(
            self, None, self.tr("Order error: ") + str(status["error"])
        )
