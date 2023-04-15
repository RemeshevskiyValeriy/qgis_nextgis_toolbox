# -*- coding: utf-8 -*-
"""
/***************************************************************************
 InputsDialog
                                 A QGIS plugin
 InputsDialog class for NextGis Toolbox
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
import uuid
import traceback
from zipfile import ZipFile

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsVectorFileWriter,
    QgsMapLayerProxyModel,
    QgsProcessingUtils,
)
from qgis.gui import QgsMapLayerComboBox

from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QLineEdit,
    QScrollArea,
    QDialogButtonBox,
    QProgressDialog,
    QApplication,
    QMessageBox,
    QCheckBox,
    QLabel,
)

from .NgToolbox import NgInputFilename, Input, NgToolgboxConnError


TEMP_FOLDER = QgsProcessingUtils.tempFolder()


class InputLayerFileWidget(QWidget):
    def __init__(self, tool_input: Input, parent=None):
        self.parent = parent
        QWidget.__init__(self)
        self.tool_input = tool_input
        # TODO: it's not working now because Toolbox api send wrong "required"
        self.valid = True
        # if not tool_input.required:
        #     self.valid = True

        self.tmp_folder = f"{TEMP_FOLDER}/{uuid.uuid4()}"
        os.mkdir(self.tmp_folder)

        self.vLayout = QVBoxLayout()
        self.vLayout.setSpacing(5)

        self.fileBrowserHLayout = QHBoxLayout()
        self.fileBrowserWidget = QWidget()
        self.fileLineEdit = QLineEdit(self.fileBrowserWidget)
        self.fileLineEdit.setPlaceholderText(self.tr("Select file"))
        self.fileBrowserHLayout.addWidget(self.fileLineEdit)
        self.fileSelectionButton = QPushButton("\u2026", self.fileBrowserWidget)
        self.fileSelectionButton.setMaximumWidth(30)
        self.fileBrowserHLayout.addWidget(self.fileSelectionButton)
        self.fileBrowserHLayout.addWidget(QLabel(self.tr("Layer to zip:")))
        self.layerCombo = QgsMapLayerComboBox(self.fileBrowserWidget)
        self.layerCombo.setAllowEmptyLayer(True)
        self.layerCombo.setFilters(QgsMapLayerProxyModel.VectorLayer)
        self.layerCombo.setCurrentIndex(0)
        self.layerCombo.setMinimumWidth(70)
        self.fileBrowserHLayout.addWidget(self.layerCombo)
        self.layerSelectionButton = QPushButton(self.tr("Pack"), self.fileBrowserWidget)
        self.layerSelectionButton.setEnabled(False)
        # self.layerSelectionButton.setMaximumWidth(65)
        self.fileBrowserHLayout.addWidget(self.layerSelectionButton)
        self.fileBrowserWidget.setLayout(self.fileBrowserHLayout)

        # TODO: it's not working now because Toolbox api send wrong "required"
        # optional_str = self.tr(" (Optinonal)") if not self.tool_input.required else ""
        # self.inputName = QLabel(f'{tool_input.title}{optional_str}:')
        self.inputName = QLabel(f"{tool_input.title}:")
        self.vLayout.addWidget(self.inputName)
        self.vLayout.addWidget(self.fileBrowserWidget)
        if tool_input.description:
            self.inputDesc = QLabel(
                self.tr('Description: ') + tool_input.description
            )
            self.inputDesc.setWordWrap(True)
            self.vLayout.addWidget(self.inputDesc)
        self.setLayout(self.vLayout)

        self.fileSelectionButton.clicked.connect(self.get_file)
        self.layerSelectionButton.clicked.connect(self.layer_to_zip)
        self.layerCombo.currentIndexChanged.connect(self.lock_pack_button)
        self.fileLineEdit.textChanged.connect(self.validate_input)

    def __del__(self):
        for temp in os.listdir(self.tmp_folder):
            os.remove(f"{self.tmp_folder}/{temp}")
        os.rmdir(self.tmp_folder)

    def get_file(self):
        filename, _ = QFileDialog.getOpenFileName(None, self.tr("Select file"), "")
        if filename:
            self.layerCombo.setCurrentIndex(0)
            self.fileLineEdit.setText(filename)

    def layer_to_zip(self):
        layer = self.layerCombo.currentLayer()

        shp_file = f"{self.tmp_folder}/{layer.name()}.shp"
        err, _ = QgsVectorFileWriter.writeAsVectorFormat(
            layer, shp_file, "utf-8", driverName="ESRI Shapefile"
        )
        if err:
            raise Exception(err)
        shp_files = os.listdir(self.tmp_folder)
        zip_file = f"{self.tmp_folder}/{layer.name()}.zip"
        with ZipFile(zip_file, "w") as myzip:
            for shp in shp_files:
                myzip.write(f"{self.tmp_folder}/{shp}", shp)

        self.fileLineEdit.setText(zip_file)

    def lock_pack_button(self):
        if self.layerCombo.currentIndex() <= 0:
            self.layerSelectionButton.setEnabled(False)
        else:
            self.layerSelectionButton.setEnabled(True)

    def validate_input(self, text):
        """TODO: It's not working with "required" attribute
        now because of Toolbox API !!!
        """
        # if not text and not self.tool_input.required:
        if not text:
            self.valid = True
            return
        # zip_file = ZipFile(text)
        # ret = zip_file.testzip()

        if os.path.isfile(text):
            self.fileLineEdit.setStyleSheet("background: transparent;")
            self.valid = True
        else:
            self.fileLineEdit.setStyleSheet("background: red;")
            self.valid = False


class InputLineWidget(QWidget):
    def __init__(self, tool_input: Input, parent=None):
        self.parent = parent
        QWidget.__init__(self)

        types_names = {
            str: self.tr("String"),
            float: self.tr("Float"),
            int: self.tr("Integer"),
            bool: self.tr("Boolean"),
        }

        self.tool_input = tool_input

        # TODO: it's not working now because Toolbox api send wrong "required"
        self.valid = True
        # if not tool_input.required:
        #     self.valid = True

        self.vLayout = QVBoxLayout()
        self.vLayout.setSpacing(5)
        foo = foo if "foo" in locals() else "default"
        # TODO: it's not working now because Toolbox api send wrong "required"
        # optional_str = self.tr(" (Optinonal)") if not self.tool_input.required else ""
        # self.inputName = QLabel(f'{tool_input.title}{optional_str}:')
        self.inputName = QLabel(f"{tool_input.title}:")
        self.inputLine = QLineEdit(self)
        self.inputLine.setPlaceholderText(types_names[self.tool_input.type_])
        self.vLayout.addWidget(self.inputName)
        self.vLayout.addWidget(self.inputLine)
        if tool_input.description:
            self.inputDesc = QLabel(
                self.tr('Description: ') + tool_input.description
            )
            self.inputDesc.setWordWrap(True)
            self.vLayout.addWidget(self.inputDesc)
        self.setLayout(self.vLayout)

        self.inputLine.textEdited.connect(self.validate_input)

    def validate_input(self, text):
        """TODO: It's not working with "required" attribute
        now because of Toolbox API !!!
        """
        # if not text and not self.tool_input.required:
        if not text:
            self.valid = True
            return
        try:
            self.tool_input.value = self.tool_input.type_(text)
            self.inputLine.setText(self.tool_input.value)
            self.inputLine.setStyleSheet("background: transparent;")
            self.valid = True
        except ValueError:
            self.inputLine.setStyleSheet("background: red;")
            self.valid = False


class InputsDialog(QDialog):
    def __init__(self, tool_id, tool_name, inputs, toolbox):
        QDialog.__init__(self)
        self.toolbox = toolbox
        self.tool_id = tool_id
        self.inputs = inputs

        self.setWindowTitle(tool_name)
        self.setMinimumSize(500, 100)

        self.layout = QVBoxLayout()
        self.scrollLayout = QVBoxLayout()
        self.scrollLayout.setSpacing(10)

        self.scrollAreaContent = QWidget()
        self.scrollAreaContent.setLayout(self.scrollLayout)

        self.scrollArea = QScrollArea()
        self.scrollArea.setHorizontalScrollBarPolicy(1)  #  1 - always off
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.scrollAreaContent)

        self.input_widgets = []
        for input in inputs:
            input_widget_class = {
                NgInputFilename: InputLayerFileWidget,
                int: InputLineWidget,
                float: InputLineWidget,
                str: InputLineWidget,
                bool: InputLineWidget,
            }[input.type_]
            input_widget = input_widget_class(input, parent=self)
            self.scrollLayout.addWidget(input_widget)
            self.input_widgets.append(input_widget)

        self.layout.addWidget(self.scrollArea)

        self.waitResultsCheckBox = QCheckBox(self.tr("Wait for results"))
        self.layout.addWidget(self.waitResultsCheckBox)
        self.wait_res = False
        self.task_id = None

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.buttonBox.addButton(self.tr("Run"), QDialogButtonBox.AcceptRole)
        self.buttonBox.accepted.connect(self.send)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

        self.scrollAreaContent.adjustSize()
        self.setLayout(self.layout)

    def prepare_inputs(self):
        if not self.validate_inputs():
            QMessageBox.about(self, None, self.tr("Fix the inputs first."))
            return False
        for input_widget in self.input_widgets:
            # TODO: it's not working now because Toolbox api send wrong "required"
            # if not input_widget.tool_input.value and not input_widget.tool_input.required:
            if (
                isinstance(input_widget, InputLineWidget)
                and not input_widget.tool_input.value
            ):
                # self.inputs.inputs.remove(input_widget.tool_input)
                input_widget.tool_input.value = ""
                continue
            if isinstance(input_widget, InputLayerFileWidget):
                if not input_widget.fileLineEdit.text():
                    # self.inputs.inputs.remove(input_widget.tool_input)
                    input_widget.tool_input.value = ""
                    continue
                try:
                    loaded_zip = self.toolbox.upload_file(
                        input_widget.fileLineEdit.text()
                    )
                except NgToolgboxConnError:
                    self.iface.messageBar().pushMessage(
                        "NextGis Toolbox", self.tr("Connection error!"), level=Qgis.Critical
                    )
                    return False
                except Exception:
                    err = traceback.format_exc()
                    QMessageBox.about(self, None, self.tr("Error uploading file"))
                    QgsMessageLog.logMessage(err, "NgToolbox", level=Qgis.Warning)
                    return False
                else:
                    input_widget.tool_input.set_value(loaded_zip)
        return True

    def validate_inputs(self):
        for input_widget in self.input_widgets:
            if not input_widget.valid:
                return False
        return True

    def send(self):
        progress = QProgressDialog(self.tr("Sending order..."), None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        progress.setValue(0)
        QApplication.processEvents()
        if self.prepare_inputs():
            try:
                resp = self.toolbox.create_order(self.tool_id, self.inputs)
                progress.cancel()
                if "exception" in resp:
                    err_text = (
                        self.tr("Error creating order! Toolbox exception: ")
                        + resp["exception"]
                    )
                    QMessageBox.about(self, None, err_text)
                else:
                    if self.waitResultsCheckBox.isChecked():
                        self.wait_res = True
                        self.task_id = resp["task_id"]
                    self.accept()
            except NgToolgboxConnError:
                self.iface.messageBar().pushMessage(
                    "NextGis Toolbox", self.tr("Connection error!"), level=Qgis.Critical
                )
                return False
            except Exception:
                err = traceback.format_exc()
                QMessageBox.about(
                    self,
                    None,
                    self.tr(
                        "Error creating order. Try again or report about the problem."
                    ),
                )
                QgsMessageLog.logMessage(err, "NgToolbox", level=Qgis.Warning)
        progress.cancel()
