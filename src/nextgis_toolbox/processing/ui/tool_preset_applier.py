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

import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, cast

from qgis.core import QgsProcessingParameterDefinition

from nextgis_toolbox.core.logging import logger
from nextgis_toolbox.nextgis_toolbox.tools.models import ToolPreset
from nextgis_toolbox.processing.parameters import (
    PresetPreparationContext,
)
from nextgis_toolbox.processing.parameters.controls import (
    ADD_RESULTS_TO_PROJECT_PARAMETER_NAME,
)
from nextgis_toolbox.processing.toolbox_algorithm import (
    ToolboxAlgorithm,
)
from nextgis_toolbox.processing.ui.compat import (
    AlgorithmDialog,
    ParametersPanel,
)


class ToolPresetApplier:
    def __init__(self, download_root: Optional[Path] = None) -> None:
        if download_root is None:
            download_root = Path(tempfile.gettempdir()) / "nextgis_toolbox"
        self._download_root = Path(download_root)

    def apply(
        self,
        dialog: AlgorithmDialog,
        algorithm: ToolboxAlgorithm,
        preset: ToolPreset,
    ) -> bool:
        algorithm_name = algorithm.name()
        logger.debug(
            f"Applying preset '{preset.alias}' to algorithm '{algorithm_name}'"
        )

        try:
            main_widget = dialog.mainWidget()
            if main_widget is None:
                raise RuntimeError("Algorithm dialog has no main widget")

            parameters = self._prepare_parameters(algorithm, preset)
            self._apply_parameters(dialog, parameters)

            logger.debug(
                f"Applied preset '{preset.alias}' to algorithm '{algorithm_name}'"
            )
            return True
        except Exception:
            logger.exception(
                f"Failed to apply preset '{preset.alias}' to algorithm '{algorithm_name}'"
            )
            return False

    def _prepare_parameters(
        self,
        algorithm: ToolboxAlgorithm,
        preset: ToolPreset,
    ) -> Dict[Optional[str], Any]:
        prepared_parameters: Dict[Optional[str], Any] = {}
        preset_context = PresetPreparationContext(
            client=algorithm.api_client(),
            algorithm_name=algorithm.name(),
            preset_alias=preset.alias,
            download_root=self._download_root,
        )

        for parameter in algorithm.tool.inputs:
            if parameter.name not in preset.inputs:
                continue

            prepared_parameters.update(
                algorithm.parameter_registry.prepare_input_preset_values(
                    parameter,
                    preset.inputs[parameter.name],
                    preset_context,
                )
            )

        return prepared_parameters

    def _apply_parameters(
        self,
        dialog: AlgorithmDialog,
        parameters: Dict[Optional[str], Any],
    ) -> None:
        parameter_names = {
            parameter.name()
            for parameter in dialog.algorithm().parameterDefinitions()
        }
        input_parameters: Dict[Optional[str], Any] = {
            name: value
            for name, value in parameters.items()
            if name in parameter_names
        }
        if ADD_RESULTS_TO_PROJECT_PARAMETER_NAME in parameter_names:
            input_parameters[ADD_RESULTS_TO_PROJECT_PARAMETER_NAME] = True

        dialog.setParameters(input_parameters)

        self._apply_output_parameters(dialog, parameters)

    def _apply_output_parameters(
        self,
        dialog: AlgorithmDialog,
        parameters: Dict[Optional[str], Any],
    ) -> None:
        parameters_panel = cast(ParametersPanel, dialog.mainWidget())
        wrappers = parameters_panel.wrappers
        processing_context = parameters_panel.processing_context
        extra_parameters = parameters_panel.extra_parameters
        destination_names = {
            parameter.name()
            for parameter in dialog.algorithm().destinationParameterDefinitions()
        }
        hidden_flag = cast(
            Any,
            QgsProcessingParameterDefinition,
        ).Flag.FlagHidden
        hidden_names = {
            parameter.name()
            for parameter in dialog.algorithm().parameterDefinitions()
            if parameter.flags() & hidden_flag
        }

        for name, value in parameters.items():
            if name in destination_names and name in wrappers:
                wrappers[name].setParameterValue(value, processing_context)
                continue

            if name in hidden_names and name not in wrappers:
                extra_parameters[name] = value
