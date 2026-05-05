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

from typing import Any, Callable, Dict, List, Optional

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingOutputDefinition,
    QgsProcessingOutputFile,
    QgsProcessingOutputString,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDateTime,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterEnum,
    QgsProcessingParameterExtent,
    QgsProcessingParameterFile,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)
from qgis.PyQt.QtCore import QCoreApplication

from nextgis_toolbox.core.compat import (
    ProcessingNumberParameterType,
)
from nextgis_toolbox.nextgis_toolbox.models.io import (
    ToolboxParameter,
)

_NGW_URL_SUFFIX = "_url"
_NGW_LOGIN_SUFFIX = "_login"
_NGW_PASSWORD_SUFFIX = "_password"


INPUT_PARAMETER_MAPPING: Dict[str, Dict[str, Any]] = {
    "string": {"class": QgsProcessingParameterString},
    "file": {"class": QgsProcessingParameterFile},
    "boolean": {"class": QgsProcessingParameterBoolean},
    "int": {
        "class": QgsProcessingParameterNumber,
        "number_type": ProcessingNumberParameterType.Integer,
    },
    "float": {
        "class": QgsProcessingParameterNumber,
        "number_type": ProcessingNumberParameterType.Double,
    },
    "single_choice": {
        "class": QgsProcessingParameterEnum,
        "multiple": False,
    },
    "multiple_choice": {
        "class": QgsProcessingParameterEnum,
        "multiple": True,
    },
    "bbox": {"class": QgsProcessingParameterExtent},
    "date": {"class": QgsProcessingParameterDateTime},
    "ngw_connection": {"class": QgsProcessingParameterString},
}

OUTPUT_PARAMETER_MAPPING: Dict[str, Any] = {
    "file": QgsProcessingOutputFile,
    "string": QgsProcessingOutputString,
}


def _apply_help(
    qgis_parameter: QgsProcessingParameterDefinition,
    input_parameter: ToolboxParameter,
) -> QgsProcessingParameterDefinition:
    """
    Attach the NextGIS Toolbox parameter description as QGIS help text.

    :param qgis_parameter: Newly created QGIS parameter.
    :param input_parameter: Source NextGIS Toolbox descriptor.

    :returns: The same parameter with help text set (mutated in-place).
    """
    if input_parameter.description:
        qgis_parameter.setHelp(input_parameter.description)
    return qgis_parameter


def create_input_parameter(
    input_parameter: ToolboxParameter,
) -> QgsProcessingParameterDefinition:
    """
    Create a QGIS input parameter from a NextGIS Toolbox definition.

    :param input_parameter: NextGIS Toolbox parameter descriptor.

    :returns: Corresponding QGIS parameter instance with help text set.
    """
    description = (
        input_parameter.alias
        or input_parameter.description
        or input_parameter.name
    )
    optional = not input_parameter.required
    parameter_config: Dict[str, Any] = INPUT_PARAMETER_MAPPING.get(
        input_parameter.parameter_type,
        {"class": QgsProcessingParameterString},
    )
    parameter_class = parameter_config["class"]

    if parameter_class is QgsProcessingParameterEnum:
        choices: List[str] = [
            choice.get("alias") or choice.get("value", "")
            for choice in (input_parameter.choices or [])
        ]
        qgis_parameter = QgsProcessingParameterEnum(
            input_parameter.name,
            description,
            options=choices,
            allowMultiple=parameter_config.get("multiple", False),
            optional=optional,
        )
        return _apply_help(qgis_parameter, input_parameter)

    if parameter_class is QgsProcessingParameterNumber:
        qgis_parameter = QgsProcessingParameterNumber(
            input_parameter.name,
            description,
            type=parameter_config["number_type"],
            optional=optional,
        )
        return _apply_help(qgis_parameter, input_parameter)

    qgis_parameter = parameter_class(
        input_parameter.name, description, optional=optional
    )
    return _apply_help(qgis_parameter, input_parameter)


def create_ngw_connection_parameters(
    input_parameter: ToolboxParameter,
) -> List[QgsProcessingParameterDefinition]:
    """
    Expand a single ``ngw_connection`` descriptor into three QGIS parameters.

    The three parameters are named ``{name}_url``, ``{name}_login``, and
    ``{name}_password``.

    :param input_parameter: NextGIS Toolbox parameter descriptor with type
        ``ngw_connection``.

    :returns: List of three :class:`QgsProcessingParameterString` instances.
    """
    optional = not input_parameter.required

    url_param = QgsProcessingParameterString(
        f"{input_parameter.name}{_NGW_URL_SUFFIX}",
        QCoreApplication.translate("NextgisToolboxAlgorithm", "Web GIS URL"),
        optional=optional,
    )
    url_param.setHelp(
        QCoreApplication.translate(
            "NextgisToolboxAlgorithm",
            "Web GIS address, e.g. https://demo.nextgis.com.",
        )
    )

    login_param = QgsProcessingParameterString(
        f"{input_parameter.name}{_NGW_LOGIN_SUFFIX}",
        QCoreApplication.translate(
            "NextgisToolboxAlgorithm",
            "Web GIS login",
        ),
        optional=True,
    )
    login_param.setHelp(
        QCoreApplication.translate(
            "NextgisToolboxAlgorithm",
            "Username for the Web GIS (leave empty if public).",
        )
    )

    password_param = QgsProcessingParameterString(
        f"{input_parameter.name}{_NGW_PASSWORD_SUFFIX}",
        QCoreApplication.translate(
            "NextgisToolboxAlgorithm",
            "Web GIS password",
        ),
        optional=True,
    )
    password_param.setHelp(
        QCoreApplication.translate(
            "NextgisToolboxAlgorithm",
            "Password for the Web GIS (leave empty if public).",
        )
    )

    return [url_param, login_param, password_param]


def create_output_parameter(
    output_parameter: ToolboxParameter,
) -> QgsProcessingOutputDefinition:
    """
    Create a QGIS output definition from a NextGIS Toolbox descriptor.

    :param output_parameter: NextGIS Toolbox output parameter descriptor.

    :returns: Corresponding QGIS output definition instance.
    """
    description = output_parameter.alias or output_parameter.name

    output_parameter_class = OUTPUT_PARAMETER_MAPPING.get(
        output_parameter.parameter_type,
        QgsProcessingOutputString,
    )

    return output_parameter_class(
        output_parameter.name,
        description,
    )


_Resolver = Callable[..., Any]


def _resolve_single_choice(
    algorithm: QgsProcessingAlgorithm,
    parameters: Dict[str, Any],
    name: str,
    context: QgsProcessingContext,
    parameter: ToolboxParameter,
) -> Optional[str]:
    choice = algorithm.parameterAsEnum(parameters, name, context)
    if not parameter.choices:
        return None
    return parameter.choices[choice]["value"]


def _resolve_multiple_choice(
    algorithm: QgsProcessingAlgorithm,
    parameters: Dict[str, Any],
    name: str,
    context: QgsProcessingContext,
    parameter: ToolboxParameter,
) -> List[str]:
    choices = algorithm.parameterAsEnums(parameters, name, context)
    if not parameter.choices:
        return []
    return [parameter.choices[choice]["value"] for choice in choices]


def _resolve_file(
    algorithm: QgsProcessingAlgorithm,
    parameters: Dict[str, Any],
    name: str,
    context: QgsProcessingContext,
    parameter: ToolboxParameter,  # noqa: ARG001
) -> str:
    return algorithm.parameterAsFile(parameters, name, context)


def _resolve_bbox(
    algorithm: QgsProcessingAlgorithm,
    parameters: Dict[str, Any],
    name: str,
    context: QgsProcessingContext,
    parameter: ToolboxParameter,  # noqa: ARG001
) -> str:
    extent = algorithm.parameterAsExtent(parameters, name, context)
    return (
        f"{extent.xMinimum()},{extent.yMinimum()},"
        f"{extent.xMaximum()},{extent.yMaximum()}"
    )


def _resolve_boolean(
    algorithm: QgsProcessingAlgorithm,
    parameters: Dict[str, Any],
    name: str,
    context: QgsProcessingContext,
    parameter: ToolboxParameter,  # noqa: ARG001
) -> bool:
    return algorithm.parameterAsBool(parameters, name, context)


def _resolve_int(
    algorithm: QgsProcessingAlgorithm,
    parameters: Dict[str, Any],
    name: str,
    context: QgsProcessingContext,
    parameter: ToolboxParameter,  # noqa: ARG001
) -> int:
    return algorithm.parameterAsInt(parameters, name, context)


def _resolve_float(
    algorithm: QgsProcessingAlgorithm,
    parameters: Dict[str, Any],
    name: str,
    context: QgsProcessingContext,
    parameter: ToolboxParameter,  # noqa: ARG001
) -> float:
    return algorithm.parameterAsDouble(parameters, name, context)


def _resolve_date(
    algorithm: QgsProcessingAlgorithm,
    parameters: Dict[str, Any],
    name: str,
    context: QgsProcessingContext,
    parameter: ToolboxParameter,  # noqa: ARG001
) -> str:
    """
    Return date as ISO-8601 string (YYYY-MM-DD).

    ``QgsProcessingParameterDateTime`` returns a ``QDateTime``; converting
    via ``parameterAsDateTime`` gives us a proper typed object instead of a
    raw string from ``parameterAsString``.
    """
    datetime = algorithm.parameterAsDateTime(parameters, name, context)
    if not datetime.isValid():
        return ""
    return datetime.toString("yyyy-MM-dd")


def _resolve_string(
    algorithm: QgsProcessingAlgorithm,
    parameters: Dict[str, Any],
    name: str,
    context: QgsProcessingContext,
    parameter: ToolboxParameter,  # noqa: ARG001
) -> str:
    return algorithm.parameterAsString(parameters, name, context)


def _resolve_ngw_connection(
    algorithm: QgsProcessingAlgorithm,
    parameters: Dict[str, Any],
    name: str,
    context: QgsProcessingContext,
    parameter: ToolboxParameter,  # noqa: ARG001
) -> Dict[str, str]:
    """
    Collect the three ``ngw_connection`` sub-fields into a single dict.

    The returned dict matches the structure expected by the NextGIS
    Toolbox API for connection parameters.

    :returns: Dict with keys ``url``, ``login``, ``password``.
    """
    return {
        "url": algorithm.parameterAsString(
            parameters,
            f"{name}{_NGW_URL_SUFFIX}",
            context,
        ),
        "login": algorithm.parameterAsString(
            parameters,
            f"{name}{_NGW_LOGIN_SUFFIX}",
            context,
        ),
        "password": algorithm.parameterAsString(
            parameters,
            f"{name}{_NGW_PASSWORD_SUFFIX}",
            context,
        ),
    }


_RESOLVER_MAPPING: Dict[str, _Resolver] = {
    "single_choice": _resolve_single_choice,
    "multiple_choice": _resolve_multiple_choice,
    "file": _resolve_file,
    "bbox": _resolve_bbox,
    "boolean": _resolve_boolean,
    "int": _resolve_int,
    "float": _resolve_float,
    "date": _resolve_date,
    "string": _resolve_string,
    "ngw_connection": _resolve_ngw_connection,
}


def resolve_parameter_value(
    parameter: ToolboxParameter,
    algorithm: QgsProcessingAlgorithm,
    parameters: Dict[str, Any],
    context: QgsProcessingContext,
) -> Any:
    """
    Resolve the runtime value of a NextGIS Toolbox parameter from QGIS inputs.

    Falls back to ``parameterAsString`` for unknown types (e.g.
    ``ngw_connection``).

    :param parameter: NextGIS Toolbox parameter descriptor.
    :param algorithm: QGIS processing algorithm instance (provides
        ``parameterAs*`` helpers).
    :param parameters: Raw parameter dict from QGIS Processing framework.
    :param context: Current processing context.

    :returns: Resolved parameter value ready to be sent to the API.
    """
    resolver = _RESOLVER_MAPPING.get(parameter.parameter_type, _resolve_string)
    return resolver(algorithm, parameters, parameter.name, context, parameter)
