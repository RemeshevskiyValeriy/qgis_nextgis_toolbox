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

from nextgis_toolbox.core.logging import logger


class TaskStatus(str, Enum):
    """Normalized task execution status."""

    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    ACCEPTED = "ACCEPTED"
    DENIED = "DENIED"
    STARTED = "STARTED"
    FAILED = "FAILED"
    SUCCESS = "SUCCESS"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"
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

        logger.warning(f"Received unknown task status value: '{value}'")

        return cls.UNKNOWN

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class TaskResult:
    """Descriptor of a single NextGIS Toolbox task result."""

    name: str
    value: Any

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "TaskResult":
        """Build a result model from a JSON payload."""
        return cls(
            name=data["name"],
            value=data["value"],
        )

    def to_json(self) -> Dict[str, Any]:
        """Serialize the result model to a JSON-compatible payload."""
        return {
            "name": self.name,
            "value": self.value,
        }


@dataclass
class ToolboxTaskInformation:
    """Descriptor of a NextGIS Toolbox task."""

    tool: str
    status: TaskStatus
    progress: Optional[float]
    error: Optional[str]
    results: List[TaskResult]
    operation: str

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "ToolboxTaskInformation":
        """Build a task model from a JSON payload."""
        raw_progress = data.get("progress")
        progress = None
        if raw_progress:
            progress = float(raw_progress)

        return cls(
            tool=data["tool"],
            status=TaskStatus.from_value(data.get("status")),
            progress=progress,
            error=data.get("error"),
            results=[
                TaskResult.from_json(result_data)
                for result_data in data.get("output", [])
            ],
            operation=data["operation"],
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
        }
