from datetime import datetime, timedelta

from app.domain.enums import SimulationLifecycle
from app.simulation.models import (
    MAX_MANUAL_STEP_SECONDS,
    MAX_SPEED_MULTIPLIER,
    MIN_SPEED_MULTIPLIER,
)
from app.simulation.time_source import TimeSource


class SimulationLifecycleError(RuntimeError):
    def __init__(self, action: str, lifecycle: SimulationLifecycle) -> None:
        self.action = action
        self.lifecycle = lifecycle
        super().__init__(f"Cannot {action} while simulation is {lifecycle.value}")


class SimulationValueError(ValueError):
    pass


class AuthoritativeSimulationClock:
    """Anchor-based clock that avoids tick accumulation and pause-time jumps."""

    def __init__(
        self,
        *,
        initial_simulated_time: datetime,
        speed_multiplier: float,
        time_source: TimeSource,
        initialized: bool = True,
    ) -> None:
        if initial_simulated_time.tzinfo is None:
            raise SimulationValueError("initial_simulated_time must be timezone-aware")
        self._validate_speed(speed_multiplier)
        self._initial_simulated_time = initial_simulated_time
        self._anchor_simulated_time = initial_simulated_time
        self._anchor_monotonic = time_source.monotonic()
        self._speed_multiplier = speed_multiplier
        self._time_source = time_source
        self._lifecycle = (
            SimulationLifecycle.READY if initialized else SimulationLifecycle.UNINITIALIZED
        )

    @property
    def lifecycle(self) -> SimulationLifecycle:
        return self._lifecycle

    @property
    def speed_multiplier(self) -> float:
        return self._speed_multiplier

    @property
    def initial_simulated_time(self) -> datetime:
        return self._initial_simulated_time

    def simulated_time(self) -> datetime:
        if self._lifecycle is not SimulationLifecycle.RUNNING:
            return self._anchor_simulated_time
        elapsed = max(0.0, self._time_source.monotonic() - self._anchor_monotonic)
        return self._anchor_simulated_time + timedelta(
            seconds=elapsed * self._speed_multiplier
        )

    def create(self) -> None:
        if self._lifecycle is SimulationLifecycle.UNINITIALIZED:
            self.reset()

    def start(self) -> None:
        self._require("start", SimulationLifecycle.READY)
        self._anchor_monotonic = self._time_source.monotonic()
        self._lifecycle = SimulationLifecycle.RUNNING

    def pause(self) -> None:
        self._require("pause", SimulationLifecycle.RUNNING)
        now = self._time_source.monotonic()
        self._anchor_simulated_time += timedelta(
            seconds=max(0.0, now - self._anchor_monotonic) * self._speed_multiplier
        )
        self._anchor_monotonic = now
        self._lifecycle = SimulationLifecycle.PAUSED

    def resume(self) -> None:
        self._require("resume", SimulationLifecycle.PAUSED)
        self._anchor_monotonic = self._time_source.monotonic()
        self._lifecycle = SimulationLifecycle.RUNNING

    def reset(self) -> None:
        self._anchor_simulated_time = self._initial_simulated_time
        self._anchor_monotonic = self._time_source.monotonic()
        self._lifecycle = SimulationLifecycle.READY

    def set_speed(self, speed_multiplier: float) -> None:
        self._validate_speed(speed_multiplier)
        now = self._time_source.monotonic()
        if self._lifecycle is SimulationLifecycle.RUNNING:
            self._anchor_simulated_time += timedelta(
                seconds=max(0.0, now - self._anchor_monotonic) * self._speed_multiplier
            )
        self._anchor_monotonic = now
        self._speed_multiplier = speed_multiplier

    def step(self, seconds: float) -> None:
        if self._lifecycle not in {
            SimulationLifecycle.READY,
            SimulationLifecycle.PAUSED,
        }:
            raise SimulationLifecycleError("step", self._lifecycle)
        if not 0 < seconds <= MAX_MANUAL_STEP_SECONDS:
            raise SimulationValueError(
                f"step seconds must be between 0 and {MAX_MANUAL_STEP_SECONDS}"
            )
        self._anchor_simulated_time += timedelta(seconds=seconds)

    def _require(self, action: str, expected: SimulationLifecycle) -> None:
        if self._lifecycle is not expected:
            raise SimulationLifecycleError(action, self._lifecycle)

    @staticmethod
    def _validate_speed(speed_multiplier: float) -> None:
        if not MIN_SPEED_MULTIPLIER <= speed_multiplier <= MAX_SPEED_MULTIPLIER:
            raise SimulationValueError(
                f"speed_multiplier must be between {MIN_SPEED_MULTIPLIER} and "
                f"{MAX_SPEED_MULTIPLIER}"
            )
