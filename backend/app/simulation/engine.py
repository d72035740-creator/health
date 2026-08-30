from collections.abc import Callable
from datetime import datetime, timezone
from threading import RLock
from uuid import NAMESPACE_URL, uuid5

from app.domain.enums import ArmSide, DataProvenance
from app.simulation.clock import AuthoritativeSimulationClock
from app.simulation.models import SimulationClockEvent, SimulationSnapshot, SyntheticPatient
from app.simulation.random_source import SimulationRandom
from app.simulation.time_source import SystemTimeSource, TimeSource


DEFAULT_SEED = 42_017
DEFAULT_SPEED_MULTIPLIER = 21_600.0
DEFAULT_SIMULATED_START = datetime(2026, 8, 30, 8, 30, tzinfo=timezone.utc)


class DigitalPatientEngine:
    """Single-session owner for identity, lifecycle, time, and deterministic RNG."""

    def __init__(
        self,
        *,
        seed: int = DEFAULT_SEED,
        initial_simulated_time: datetime = DEFAULT_SIMULATED_START,
        speed_multiplier: float = DEFAULT_SPEED_MULTIPLIER,
        time_source: TimeSource | None = None,
        initialized: bool = True,
    ) -> None:
        self._lock = RLock()
        self._time_source = time_source or SystemTimeSource()
        self._seed = seed
        self._random = SimulationRandom(seed)
        self._clock = AuthoritativeSimulationClock(
            initial_simulated_time=initial_simulated_time,
            speed_multiplier=speed_multiplier,
            time_source=self._time_source,
            initialized=initialized,
        )
        stable_key = f"DEMO-001:{seed}:{initial_simulated_time.isoformat()}"
        self._simulation_id = str(uuid5(NAMESPACE_URL, f"aequor:{stable_key}"))
        self._patient = SyntheticPatient(
            patient_id="DEMO-001",
            display_name="Maya Sen",
            age_years=38,
            sex="FEMALE",
            dominant_arm=ArmSide.RIGHT,
            created_at=initial_simulated_time,
            synthetic=True,
        )
        self._reset_hooks: list[Callable[[], None]] = []

    @property
    def random_source(self) -> SimulationRandom:
        return self._random

    def register_reset_hook(self, hook: Callable[[], None]) -> None:
        """Extension point for future simulation modules; none are registered in Phase 1."""
        with self._lock:
            self._reset_hooks.append(hook)

    def snapshot(self) -> SimulationSnapshot:
        with self._lock:
            return SimulationSnapshot(
                simulation_id=self._simulation_id,
                patient=self._patient,
                seed=self._seed,
                lifecycle=self._clock.lifecycle,
                wall_clock_time=self._time_source.wall_clock_time(),
                simulated_time=self._clock.simulated_time(),
                speed_multiplier=self._clock.speed_multiplier,
                data_provenance=DataProvenance.SIMULATED,
            )

    def clock_event(self) -> SimulationClockEvent:
        snapshot = self.snapshot()
        return SimulationClockEvent(
            simulation_id=snapshot.simulation_id,
            lifecycle=snapshot.lifecycle,
            wall_clock_time=snapshot.wall_clock_time,
            simulated_time=snapshot.simulated_time,
            speed_multiplier=snapshot.speed_multiplier,
        )

    def create(self) -> SimulationSnapshot:
        with self._lock:
            self._clock.create()
            return self.snapshot()

    def start(self) -> SimulationSnapshot:
        with self._lock:
            self._clock.start()
            return self.snapshot()

    def pause(self) -> SimulationSnapshot:
        with self._lock:
            self._clock.pause()
            return self.snapshot()

    def resume(self) -> SimulationSnapshot:
        with self._lock:
            self._clock.resume()
            return self.snapshot()

    def reset(self) -> SimulationSnapshot:
        with self._lock:
            self._clock.reset()
            self._random.reset()
            for hook in self._reset_hooks:
                hook()
            return self.snapshot()

    def set_speed(self, speed_multiplier: float) -> SimulationSnapshot:
        with self._lock:
            self._clock.set_speed(speed_multiplier)
            return self.snapshot()

    def step(self, seconds: float) -> SimulationSnapshot:
        with self._lock:
            self._clock.step(seconds)
            return self.snapshot()


simulation_engine = DigitalPatientEngine()

