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
from enum import Enum
from typing import Any, Dict, List, Optional


class TaskStatus(str, Enum):
    """Normalized task execution status."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    STARTED = "STARTED"
    PENDING = "PENDING"
    UNKNOWN = "UNKNOWN"

    @classmethod
    def from_value(cls, value: Optional[str]) -> "TaskStatus":
        """Convert raw API value to enum."""
        if value is None:
            return cls.UNKNOWN

        normalized_value = value.upper()
        for status in cls:
            if status.value == normalized_value:
                return status

        return cls.UNKNOWN

    def __str__(self) -> str:
        return self.value


@dataclass
class ToolboxResult:
    """Descriptor of a single NextGIS Toolbox task result."""

    name: str
    result_type: str
    value: str

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "ToolboxResult":
        """Build a result model from a JSON payload."""
        return cls(
            name=data["name"],
            result_type=data["type"],
            value=data["value"],
        )

    def to_json(self) -> Dict[str, Any]:
        """Serialize the result model to a JSON-compatible payload."""
        return {
            "name": self.name,
            "type": self.result_type,
            "value": self.value,
        }


@dataclass
class ToolboxTask:
    """Descriptor of a NextGIS Toolbox task."""

    tool: str
    status: TaskStatus
    progress: float
    error: Optional[str]
    results: List[ToolboxResult]
    operation: str
    state: TaskStatus

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "ToolboxTask":
        """Build a task model from a JSON payload."""
        return cls(
            tool=data["tool"],
            status=TaskStatus.from_value(data.get("status")),
            progress=float(data.get("progress", 0.0)),
            error=data.get("error"),
            results=[
                ToolboxResult.from_json(result_data)
                for result_data in data.get("output", [])
            ],
            operation=data["operation"],
            state=TaskStatus.from_value(data.get("state")),
        )

    def to_json(self) -> Dict[str, Any]:
        """Serialize the task model to a JSON-compatible payload."""
        return {
            "tool": self.tool,
            "status": str(self.status),
            "progress": self.progress,
            "error": self.error,
            "output": [result.to_json() for result in self.results],
            "operation": self.operation,
            "state": str(self.state),
        }
