# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ResultsDialog
                                 A QGIS plugin
 ResultsDialog class for NextGis Toolbox
                             -------------------
        begin                : 2023-02-13
        git sha              : $Format:%H$
        copyright            : (C) 2023 by NextGIS
        email                : info@nextgis.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os
import traceback

from qgis.core import Qgis, QgsMessageLog
from qgis.PyQt.QtCore import Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QTableWidgetItem,
)
from qgis.PyQt.uic import loadUiType

from .NgToolbox import API_URL, Results, Toolbox, ToolboxConnError

PLUGIN_DIR = os.path.dirname(__file__)

RESULTS_FORM_CLASS, _ = loadUiType(os.path.join(PLUGIN_DIR, "ui/ResultsDialog.ui"))


class ResultsDialog(QDialog, RESULTS_FORM_CLASS):
    def __init__(self, results: Results, toolbox: Toolbox, parent=None):
        super(ResultsDialog, self).__init__(parent)
        self.setupUi(self)

        self.results = results
        self.toolbox = toolbox

        self.tableWidget.clearContents()
        self.tableWidget.setRowCount(len(results.results))
        for row, result in enumerate(results):
            titleItem = QTableWidgetItem(result.title)
            titleItem.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.tableWidget.setItem(row, 0, titleItem)

            valueItem = QTableWidgetItem(result.value)
            self.tableWidget.setItem(row, 1, valueItem)

            if API_URL in result.value:
                getButton = QPushButton(self.tr("Get"))
                getButton.clicked.connect(self.get_result)
                self.tableWidget.setCellWidget(row, 1, getButton)

    def get_result(self):
        row = self.tableWidget.currentRow()
        link = self.tableWidget.item(row, 1).text()

        res_dir = QFileDialog.getExistingDirectory(
            None, self.tr("Choose directory to save resulsts")
        )
        if not res_dir:
            return

        progress = QProgressDialog(self.tr("Downloading results..."), None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        progress.setValue(0)
        QApplication.processEvents()
        try:
            _ = self.toolbox.orders_man.download_file(link, res_dir)
            # QDesktopServices.openUrl(QUrl.fromLocalFile(result))
            QDesktopServices.openUrl(QUrl.fromLocalFile(res_dir))
        except ToolboxConnError:
            self.iface.messageBar().pushMessage(
                "NextGis Toolbox", self.tr("Connection error!"), level=Qgis.Critical
            )
        except Exception:
            err = traceback.format_exc()
            QMessageBox.about(self, None, self.tr("Error downloading result file."))
            QgsMessageLog.logMessage(err, "NgToolbox", level=Qgis.Warning)
        finally:
            progress.cancel()
