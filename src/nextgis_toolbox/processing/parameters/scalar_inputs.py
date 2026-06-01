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

from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Optional,
    Sequence,
    Type,
    cast,
)

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterDateTime,
    QgsProcessingParameterDefinition,
    QgsProcessingParameterExtent,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
)

from nextgis_toolbox.core.compat import ProcessingNumberParameterType
from nextgis_toolbox.nextgis_toolbox.tools.models import (
    InputParameterType,
    ToolInputParameter,
)
from nextgis_toolbox.processing.parameters.common import (
    InputParameterAdapter,
    InputParameterRepresentation,
    PresetPreparationContext,
    apply_parameter_help,
)

if TYPE_CHECKING:
    from nextgis_toolbox.processing.parameters.registry import (
        InputParameterAdapterRegistry,
    )

RuntimeResolver = Callable[
    [
        QgsProcessingAlgorithm,
        Dict[Optional[str], Any],
        str,
        QgsProcessingContext,
    ],
    Any,
]
PresetConverter = Callable[[Any], Any]


@dataclass(frozen=True)
class ScalarAdapterDefinition:
    parameter_type: InputParameterType
    parameter_class: Any
    resolver: RuntimeResolver
    preset_converter: PresetConverter
    number_type: Optional[ProcessingNumberParameterType] = None


class ScalarInputAdapter(InputParameterAdapter):
    def __init__(
        self,
        parameter_class: Type[QgsProcessingParameterDefinition],
        resolver: RuntimeResolver,
        *,
        preset_converter: Optional[PresetConverter] = None,
        number_type: Optional[ProcessingNumberParameterType] = None,
    ) -> None:
        if (
            parameter_class is QgsProcessingParameterNumber
            and number_type is None
        ):
            raise ValueError("Number parameters require explicit number_type")

        self._parameter_class = parameter_class
        self._resolver = resolver
        self._preset_converter = preset_converter or (lambda value: value)
        self._number_type = number_type

    def create_representation(
        self,
        parameter: ToolInputParameter,
    ) -> InputParameterRepresentation:
        optional = not parameter.required
        label = parameter.label

        if self._parameter_class is QgsProcessingParameterNumber:
            qgis_parameter = QgsProcessingParameterNumber(
                parameter.name,
                label,
                type=cast(
                    ProcessingNumberParameterType,
                    self._number_type,
                ),
                optional=optional,
            )
        else:
            qgis_parameter = self._parameter_class(
                parameter.name,
                label,
                optional=optional,
            )

        return InputParameterRepresentation(
            parameters=[
                apply_parameter_help(
                    qgis_parameter,
                    parameter.description,
                )
            ]
        )

    def prepare_preset_values(
        self,
        parameter: ToolInputParameter,
        value: Any,
        preset_context: PresetPreparationContext,
    ) -> Dict[str, Any]:
        del preset_context
        return {parameter.name: self._preset_converter(value)}

    def resolve_runtime_value(
        self,
        parameter: ToolInputParameter,
        algorithm: QgsProcessingAlgorithm,
        parameters: Dict[Optional[str], Any],
        context: QgsProcessingContext,
    ) -> Any:
        return self._resolver(algorithm, parameters, parameter.name, context)


class ScalarRuntimeValueResolver:
    def resolve_string(
        self,
        algorithm: QgsProcessingAlgorithm,
        parameters: Dict[Optional[str], Any],
        name: str,
        context: QgsProcessingContext,
    ) -> str:
        return algorithm.parameterAsString(parameters, name, context)

    def resolve_boolean(
        self,
        algorithm: QgsProcessingAlgorithm,
        parameters: Dict[Optional[str], Any],
        name: str,
        context: QgsProcessingContext,
    ) -> bool:
        return algorithm.parameterAsBool(parameters, name, context)

    def resolve_int(
        self,
        algorithm: QgsProcessingAlgorithm,
        parameters: Dict[Optional[str], Any],
        name: str,
        context: QgsProcessingContext,
    ) -> int:
        return algorithm.parameterAsInt(parameters, name, context)

    def resolve_float(
        self,
        algorithm: QgsProcessingAlgorithm,
        parameters: Dict[Optional[str], Any],
        name: str,
        context: QgsProcessingContext,
    ) -> float:
        return algorithm.parameterAsDouble(parameters, name, context)

    def resolve_bbox(
        self,
        algorithm: QgsProcessingAlgorithm,
        parameters: Dict[Optional[str], Any],
        name: str,
        context: QgsProcessingContext,
    ) -> str:
        extent = algorithm.parameterAsExtent(parameters, name, context)
        return (
            f"{extent.xMinimum()},{extent.yMinimum()},"
            f"{extent.xMaximum()},{extent.yMaximum()}"
        )

    def resolve_date(
        self,
        algorithm: QgsProcessingAlgorithm,
        parameters: Dict[Optional[str], Any],
        name: str,
        context: QgsProcessingContext,
    ) -> str:
        datetime = algorithm.parameterAsDateTime(parameters, name, context)
        if not datetime.isValid():
            return ""
        return datetime.toString("yyyy-MM-dd")


class ScalarPresetValueConverter:
    def pass_through(self, value: Any) -> Any:
        return value

    def coerce_int(self, value: Any) -> Any:
        if isinstance(value, str):
            return int(value)
        return value

    def coerce_float(self, value: Any) -> Any:
        if isinstance(value, str):
            return float(value)
        return value

    def coerce_boolean(self, value: Any) -> Any:
        if isinstance(value, str):
            return value.lower() in {"1", "true", "yes", "on"}
        return value


class ScalarInputAdapterFactory:
    def __init__(
        self,
        runtime_resolver: Optional[ScalarRuntimeValueResolver] = None,
        preset_converter: Optional[ScalarPresetValueConverter] = None,
    ) -> None:
        self._runtime_resolver = (
            runtime_resolver or ScalarRuntimeValueResolver()
        )
        self._preset_converter = (
            preset_converter or ScalarPresetValueConverter()
        )

    def register_defaults(
        self, registry: "InputParameterAdapterRegistry"
    ) -> None:
        for definition in self._definitions():
            registry.register(
                definition.parameter_type,
                self._create_adapter(definition),
            )

    def _definitions(self) -> Sequence[ScalarAdapterDefinition]:
        return (
            ScalarAdapterDefinition(
                InputParameterType.STRING,
                QgsProcessingParameterString,
                self._runtime_resolver.resolve_string,
                self._preset_converter.pass_through,
            ),
            ScalarAdapterDefinition(
                InputParameterType.BOOLEAN,
                QgsProcessingParameterBoolean,
                self._runtime_resolver.resolve_boolean,
                self._preset_converter.coerce_boolean,
            ),
            ScalarAdapterDefinition(
                InputParameterType.INTEGER,
                QgsProcessingParameterNumber,
                self._runtime_resolver.resolve_int,
                self._preset_converter.coerce_int,
                ProcessingNumberParameterType.Integer,
            ),
            ScalarAdapterDefinition(
                InputParameterType.FLOAT,
                QgsProcessingParameterNumber,
                self._runtime_resolver.resolve_float,
                self._preset_converter.coerce_float,
                ProcessingNumberParameterType.Double,
            ),
            ScalarAdapterDefinition(
                InputParameterType.BBOX,
                QgsProcessingParameterExtent,
                self._runtime_resolver.resolve_bbox,
                self._preset_converter.pass_through,
            ),
            ScalarAdapterDefinition(
                InputParameterType.DATE,
                QgsProcessingParameterDateTime,
                self._runtime_resolver.resolve_date,
                self._preset_converter.pass_through,
            ),
        )

    def _create_adapter(
        self,
        definition: ScalarAdapterDefinition,
    ) -> ScalarInputAdapter:
        return ScalarInputAdapter(
            definition.parameter_class,
            definition.resolver,
            preset_converter=definition.preset_converter,
            number_type=definition.number_type,
        )
