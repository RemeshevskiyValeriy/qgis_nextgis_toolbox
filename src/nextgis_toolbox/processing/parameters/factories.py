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

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from nextgis_toolbox.processing.parameters.choice_inputs import (
    ChoiceInputAdapterFactory,
)
from nextgis_toolbox.processing.parameters.file_input import (
    FileInputAdapterFactory,
)
from nextgis_toolbox.processing.parameters.ngw_connection import (
    NgwConnectionInputAdapterFactory,
)
from nextgis_toolbox.processing.parameters.output_adapters import (
    OutputParameterAdapterFactory,
)
from nextgis_toolbox.processing.parameters.scalar_inputs import (
    ScalarInputAdapterFactory,
)

if TYPE_CHECKING:
    from nextgis_toolbox.processing.parameters.registry import (
        InputParameterAdapterRegistry,
        OutputParameterAdapterRegistry,
    )


@dataclass
class BuiltinParameterAdapterFactory:
    scalar_factory: ScalarInputAdapterFactory = field(
        default_factory=ScalarInputAdapterFactory
    )
    file_factory: FileInputAdapterFactory = field(
        default_factory=FileInputAdapterFactory
    )
    choice_factory: ChoiceInputAdapterFactory = field(
        default_factory=ChoiceInputAdapterFactory
    )
    ngw_connection_factory: NgwConnectionInputAdapterFactory = field(
        default_factory=NgwConnectionInputAdapterFactory
    )
    output_factory: OutputParameterAdapterFactory = field(
        default_factory=OutputParameterAdapterFactory
    )

    def register_defaults(
        self,
        input_registry: "InputParameterAdapterRegistry",
        output_registry: "OutputParameterAdapterRegistry",
    ) -> None:
        self.scalar_factory.register_defaults(input_registry)
        self.file_factory.register_defaults(input_registry)
        self.choice_factory.register_defaults(input_registry)
        self.ngw_connection_factory.register_defaults(input_registry)
        self.output_factory.register_defaults(output_registry)
