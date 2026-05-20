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
from enum import Enum
from typing import Any, Dict, List, Optional


class SortBy(str, Enum):
    ID = "id"
    NAME = "name"
    ALIAS = "alias"

    def __str__(self) -> str:
        return self.value


@dataclass
class ToolboxTag:
    """Descriptor of a NextGIS Toolbox tag."""

    id: int
    alias: str
    icon: str
    tool_ids: List[int]

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "ToolboxTag":
        """Build a tag model from a JSON payload."""
        return cls(
            id=data["id"],
            alias=data["alias"],
            icon=data["icon"],
            tool_ids=data.get("tools", []),
        )

    def to_json(self) -> Dict[str, Any]:
        """Serialize the tag model to a JSON-compatible payload."""
        return {
            "id": self.id,
            "alias": self.alias,
            "icon": self.icon,
            "tools": self.tool_ids,
        }


@dataclass
class ToolboxTool:
    """Descriptor of a NextGIS Toolbox tool."""

    id: int
    name: str
    alias: str
    description: str
    is_dev: bool
    is_free: bool
    is_new: bool
    is_featured: bool
    can_run: bool
    tag_ids: List[int]
    tags: List[ToolboxTag] = field(default_factory=list)
    inputs: List["ToolboxParameter"] = field(default_factory=list)
    outputs: List["ToolboxParameter"] = field(default_factory=list)
    help: Optional[str] = None

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "ToolboxTool":
        """Build a tool model from a JSON payload."""
        return cls(
            id=data["id"],
            name=data["name"],
            alias=data["alias"],
            description=data["description"],
            is_dev=data["is_dev"],
            is_free=data["is_free"],
            is_new=data["is_new"],
            is_featured=data["is_featured"],
            can_run=data["can_run"],
            tag_ids=data.get("tags", []),
            inputs=[
                ToolboxParameter.from_json(parameter_data)
                for parameter_data in data.get("inputs", [])
            ],
            outputs=[
                ToolboxParameter.from_json(parameter_data)
                for parameter_data in data.get("outputs", [])
            ],
            help=data.get("docs"),
        )

    def to_json(self) -> Dict[str, Any]:
        """Serialize the tool model to a JSON-compatible payload."""
        tag_ids = self.tag_ids or [tag.id for tag in self.tags]

        return {
            "id": self.id,
            "name": self.name,
            "alias": self.alias,
            "description": self.description,
            "is_dev": self.is_dev,
            "is_free": self.is_free,
            "is_new": self.is_new,
            "is_featured": self.is_featured,
            "can_run": self.can_run,
            "tags": tag_ids,
            "inputs": [parameter.to_json() for parameter in self.inputs],
            "outputs": [parameter.to_json() for parameter in self.outputs],
            "docs": self.help,
        }


@dataclass(frozen=True)
class ToolboxParameter:
    """Immutable descriptor of a Toolbox input or output parameter."""

    name: str
    parameter_type: str
    alias: Optional[str]
    description: Optional[str]
    required: bool
    choices: Optional[List[Dict[str, Any]]]

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "ToolboxParameter":
        """Build a parameter model from a JSON payload."""
        return cls(
            name=data["name"],
            parameter_type=data["type"],
            alias=data.get("alias"),
            description=data.get("description"),
            required=data.get("required", False),
            choices=data.get("choices"),
        )

    def to_json(self) -> Dict[str, Any]:
        """Serialize the parameter model to a JSON-compatible payload."""
        return {
            "name": self.name,
            "type": self.parameter_type,
            "alias": self.alias,
            "description": self.description,
            "required": self.required,
            "choices": self.choices,
        }
