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

import random
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from nextgis_toolbox.nextgis_toolbox.tasks.models import TaskStatus

RandomUniform = Callable[[float, float], float]


class TaskExecutionState(str, Enum):
    """Represent a client-side task execution state."""

    PREPARING = "PREPARING"
    UPLOADING = "UPLOADING"
    SUBMITTING = "SUBMITTING"
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    FINISHING = "FINISHING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELED_BY_USER = "CANCELED_BY_USER"


@dataclass(frozen=True)
class TaskExecutionSnapshot:
    """Store the current task execution state."""

    task_id: Optional[str]
    backend_status: TaskStatus
    execution_state: TaskExecutionState
    progress: Optional[float]
    error: Optional[str]
    elapsed_seconds: float


class TaskPollingPolicy:
    """Compute polling intervals for Toolbox task execution."""

    _PENDING_INTERVALS = (1.0, 2.0, 3.0, 5.0, 10.0)

    def __init__(
        self,
        *,
        jitter_enabled: bool = True,
        random_uniform: Optional[RandomUniform] = None,
    ) -> None:
        """Initialize polling policy."""
        self._jitter_enabled = jitter_enabled
        self._random_uniform = random_uniform or random.uniform

    def next_interval(
        self,
        snapshot: TaskExecutionSnapshot,
        *,
        state_elapsed_seconds: float,
        state_poll_count: int,
    ) -> float:
        """Return the next polling interval in seconds."""
        if snapshot.execution_state == TaskExecutionState.PENDING:
            interval = self._pending_interval(state_poll_count)
        elif snapshot.execution_state == TaskExecutionState.RUNNING:
            interval = self._running_interval(snapshot.elapsed_seconds)
        elif snapshot.execution_state == TaskExecutionState.FINISHING:
            interval = self._finishing_interval(state_elapsed_seconds)
        else:
            return 0.0

        if not self._jitter_enabled or interval <= 0.0:
            return interval

        return interval * self._random_uniform(0.85, 1.15)

    def _pending_interval(self, state_poll_count: int) -> float:
        index = max(state_poll_count - 1, 0)
        index = min(index, len(self._PENDING_INTERVALS) - 1)
        return self._PENDING_INTERVALS[index]

    def _running_interval(self, elapsed_seconds: float) -> float:
        if elapsed_seconds < 10.0:
            return 1.0
        if elapsed_seconds < 60.0:
            return 5.0
        if elapsed_seconds < 600.0:
            return 15.0
        if elapsed_seconds < 1800.0:
            return 30.0
        if elapsed_seconds < 3600.0:
            return 60.0
        return 300.0

    def _finishing_interval(self, state_elapsed_seconds: float) -> float:
        if state_elapsed_seconds < 30.0:
            return 2.0
        if state_elapsed_seconds < 300.0:
            return 10.0
        return 30.0
