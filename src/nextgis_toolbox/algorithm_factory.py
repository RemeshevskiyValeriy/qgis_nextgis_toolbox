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

import os
import traceback
import typing
import uuid
from time import sleep
from zipfile import ZipFile

from qgis.core import (
    Qgis,
    QgsMessageLog,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingException,
    QgsProcessingOutputBoolean,
    QgsProcessingOutputFile,
    QgsProcessingOutputNumber,
    QgsProcessingOutputRasterLayer,
    QgsProcessingOutputString,
    QgsProcessingOutputVectorLayer,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterFile,
    QgsProcessingParameterFileDestination,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterString,
    QgsProcessingParameterVectorDestination,
    QgsProcessingParameterVectorLayer,
    QgsProcessingUtils,
    QgsRasterLayer,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QCoreApplication
from qgis.utils import iface

from nextgis_toolbox.nextgis_toolbox import ToolboxConnError, ToolboxIOFilename

TEMP_FOLDER = QgsProcessingUtils.tempFolder()

VECTOR_EXT = ["shp", "geojson", "kml|kmz", "kml", "gpkg"]
RASTER_EXT = [
    "tiff",
    "tif",
]
EXT2DRIVER = {
    "shp": "ESRI Shapefile",
    "geojson": "GeoJSON",
    "gpkg": "GPKG",
    "kml": "KML",
    "tif": "GTiff",
}

OUT_SELECTOR = {
    bool: QgsProcessingOutputBoolean,
    int: QgsProcessingOutputNumber,
    float: QgsProcessingOutputNumber,
    str: QgsProcessingOutputString,
}


def inp_selector(
    name: str,
    description: str,
    type_: typing.Union[ToolboxIOFilename, str, int, float, bool],
    required: bool,
    extension: str,
    **kwargs,
) -> QgsProcessingParameterDefinition:
    if description and len(description) > 70:
        description = split_desc(description)
    if type_ == ToolboxIOFilename:
        if extension in VECTOR_EXT:
            return QgsProcessingParameterVectorLayer(
                name,
                description,
                [QgsProcessing.TypeVectorAnyGeometry],
                optional=True,
                # optional=not required
            )
        elif extension in RASTER_EXT:
            return QgsProcessingParameterRasterLayer(
                name,
                description,
                optional=True,
                # optional=not required
            )
        else:
            return QgsProcessingParameterFile(
                name,
                description,
                optional=True,
                # optional=not required
            )
    elif isinstance(type_, bool):
        return QgsProcessingParameterBoolean(
            name,
            description,
            optional=True,
            # optional=not required
        )
    elif isinstance(type_, int):
        return QgsProcessingParameterNumber(
            name,
            description,
            type=0,
            optional=True,
            # optional=not required
        )
    elif isinstance(type_, float):
        return QgsProcessingParameterNumber(
            name,
            description,
            type=1,
            optional=True,
            # optional=not required
        )
    elif isinstance(type_, str):
        return QgsProcessingParameterString(
            name,
            description,
            optional=True,
            # optional=not required
        )


def save_layer(layer, folder, ext):
    ext = ext.split("|")[0]
    tmp_file = f"{folder}/{layer.name()}.{ext}"
    err, _ = QgsVectorFileWriter.writeAsVectorFormat(
        layer, tmp_file, "utf-8", driverName=EXT2DRIVER[ext]
    )
    if err:
        raise Exception(err)
    return tmp_file


def make_zip(folder, name):
    layer_files = os.listdir(folder)
    zip_file = f"{folder}/{name}.zip"
    with ZipFile(zip_file, "w") as myzip:
        for layer_file in layer_files:
            myzip.write(f"{folder}/{layer_file}", layer_file)
    return zip_file


def split_desc(text):
    lines = []
    line = ""
    for word in text.split(" "):
        line += f"{word} "
        if len(line) > 70:
            lines.append(line)
            line = ""
    lines.append(line)
    return "\n".join(lines)


def algorithm_class_factory(
    tool_id, name, group, description, inputs, outputs, toolbox
):
    class TestPluginAlgorithm(QgsProcessingAlgorithm):
        inps = inputs
        outs = outputs
        tb = toolbox

        for inp in inputs:
            exec(f"""{inp.name} = "{inp.name}" """)

        for out in outputs:
            exec(f"""{out.name} = "{out.name}" """)

        OUTPUT = "OUTPUT"

        def uploadToToolbox(self, src, ext, is_file=False):
            tmp_folder = f"{TEMP_FOLDER}/{uuid.uuid4()}"
            os.mkdir(tmp_folder)
            try:
                src_f = src
                if not is_file:
                    src_f = save_layer(src, tmp_folder, ext)
                    if len(os.listdir(tmp_folder)) > 1:
                        src_f = make_zip(tmp_folder, src.name())
                file_id = self.tb.upload_file(src_f)
            except Exception:
                e = traceback.format_exc()
                iface.messageBar().pushMessage(
                    self.tr("Error uploading file! Layer: "),
                    level=Qgis.Critical,
                )
                QgsMessageLog.logMessage(
                    f"Error uploading file! Exception: {e}",
                    "NgToolbox",
                    level=Qgis.Critical,
                )
                file_id = None
            finally:
                for temp in os.listdir(tmp_folder):
                    os.remove(f"{tmp_folder}/{temp}")
                os.rmdir(tmp_folder)

            return file_id

        def setParameter(self, inp, parameters, context):
            if inp.type_ in (bool, int, float, str):
                parameter = {
                    bool: self.parameterAsBool,
                    int: self.parameterAsInt,
                    float: self.parameterAsDouble,
                    str: self.parameterAsString,
                }[inp.type_](parameters, inp.name, context)
            else:
                if inp.extension in VECTOR_EXT:
                    lyr = self.parameterAsVectorLayer(
                        parameters, inp.name, context
                    )
                    parameter = self.uploadToToolbox(lyr, inp.extension)
                elif inp.extension in RASTER_EXT:
                    lyr = self.parameterAsRasterLayer(
                        parameters, inp.name, context
                    )
                    parameter = self.uploadToToolbox(lyr, inp.extension)
                else:
                    src = self.parameterAsFile(parameters, inp.name, context)
                    parameter = self.uploadToToolbox(src, inp.extension, True)

                if not parameter:
                    raise Exception("Error uploading file to server!")

            inp.set_value(parameter)

        def initAlgorithm(self, config):
            for inp in self.inps:
                self.addParameter(inp_selector(**inp.__dict__))

            for out in self.outs:
                desc = out.description
                if not desc:
                    desc = out.title
                if len(desc) > 70:
                    desc = split_desc(desc)
                if out.type_ == ToolboxIOFilename:
                    if out.extension and out.extension in VECTOR_EXT:
                        self.addParameter(
                            QgsProcessingParameterVectorDestination(
                                out.name, desc, optional=True
                            )
                        )
                        self.addOutput(
                            QgsProcessingOutputVectorLayer(
                                out.name,
                                desc,
                                QgsProcessing.SourceType.TypeVectorAnyGeometry,
                            )
                        )
                    elif out.extension and out.extension in RASTER_EXT:
                        self.addParameter(
                            QgsProcessingParameterRasterDestination(
                                out.name, desc, optional=True
                            )
                        )
                        self.addOutput(
                            QgsProcessingOutputRasterLayer(out.name, desc)
                        )
                    else:
                        self.addParameter(
                            QgsProcessingParameterFileDestination(
                                out.name,
                                desc,
                                f"(*.{out.extension})",
                                optional=True,
                            )
                        )
                        self.addOutput(QgsProcessingOutputFile(out.name, desc))
                else:
                    self.addOutput(OUT_SELECTOR[out.type_](out.name, desc))

        def processAlgorithm(self, parameters, context, feedback):
            for inp in self.inps:
                self.setParameter(inp, parameters, context)

            out_files = {}
            for out in self.outs:
                if out.type_ == ToolboxIOFilename:
                    if (
                        out.extension
                        and out.extension in VECTOR_EXT + RASTER_EXT
                    ):
                        out_files[out.name] = self.parameterAsOutputLayer(
                            parameters, out.name, context
                        )
                    else:
                        out_files[out.name] = self.parameterAsFileOutput(
                            parameters, out.name, context
                        )

            order_data = self.tb.create_order(self.name(), self.inps)
            task_id = order_data["task_id"]
            feedback.setProgress(1)
            while not feedback.isCanceled():
                try:
                    status = self.tb.orders_man.get_status(task_id)
                except ToolboxConnError:
                    self.iface.messageBar().pushMessage(
                        "NextGis Toolbox",
                        self.tr("Connection error!"),
                        level=Qgis.Critical,
                    )
                    raise

                if status["state"] == "SUCCESS":
                    feedback.setProgress(99)
                    break
                elif status["state"] == "FAILED":
                    feedback.reportError(
                        self.tr("Error executing task:") + str(status["error"])
                    )
                    return {}
                feedback.pushInfo(self.tr("Waiting for results..."))
                feedback.setProgress(int(status["progress"]))
                sleep(3)
            else:
                feedback.pushInfo(
                    self.tr(
                        "Waiting for results is canceled! "
                        "But task still working on NextGIS Toolbox server."
                    )
                )
                return {}

            results = {}
            for res in status["output"]:
                results[res["name"]] = res["value"]
                if res["name"] in out_files:
                    d, f = os.path.split(out_files[res["name"]])
                    feedback.pushInfo(
                        self.tr("Download result: " + res["name"])
                    )
                    feedback.pushInfo(
                        self.tr(
                            "Result file destination: "
                            + out_files[res["name"]]
                        )
                    )

                    results[res["name"]] = self.tb.orders_man.download_file(
                        res["value"], d, f
                    )

                    _, ext = os.path.splitext(results[res["name"]])
                    ext = ext.lstrip(".")
                    if ext in VECTOR_EXT + RASTER_EXT:
                        if ext in VECTOR_EXT:
                            layer = QgsVectorLayer(
                                results[res["name"]], res["name"], "ogr"
                            )
                        elif ext in RASTER_EXT:
                            layer = QgsRasterLayer(
                                results[res["name"]], res["name"], "gdal"
                            )

                        if not layer.isValid():
                            raise QgsProcessingException(
                                self.tr("Error loading output layer! File: ")
                                + results[res["name"]]
                            )

                        context.temporaryLayerStore().addMapLayer(layer)
                        context.addLayerToLoadOnCompletion(
                            layer.id(),
                            QgsProcessingContext.LayerDetails(
                                res["name"], context.project(), res["name"]
                            ),
                        )
                        results[res["name"]] = layer.id()

            feedback.setProgress(100)
            return results

        def name(self):
            return tool_id

        def displayName(self):
            return name

        def outputName(self):
            return self.displayName()

        def group(self):
            return self.groupId()

        def groupId(self):
            return group

        def shortHelpString(self):
            return description

        def tr(self, string):
            return QCoreApplication.translate("TestPluginAlgorithm", string)

        def createInstance(self):
            return TestPluginAlgorithm()

    return TestPluginAlgorithm
