from datetime import datetime, timedelta, timezone

import pytest

from app.domain.enums import SimulationLifecycle
from app.simulation.clock import SimulationLifecycleError, SimulationValueError
from app.simulation.engine import DigitalPatientEngine
from app.simulation.time_source import TimeSource


class FakeTimeSource(TimeSource):
    def __init__(self) -> None:
        self._monotonic = 100.0
        self._wall = datetime(2026, 8, 30, 10, 0, tzinfo=timezone.utc)

    def monotonic(self) -> float:
        return self._monotonic

    def wall_clock_time(self) -> datetime:
        return self._wall

    def advance(self, seconds: float) -> None:
        self._monotonic += seconds
        self._wall += timedelta(seconds=seconds)


def make_engine(
    time_source: FakeTimeSource,
    *,
    seed: int = 42_017,
    speed: float = 21_600,
) -> DigitalPatientEngine:
    return DigitalPatientEngine(
        seed=seed,
        initial_simulated_time=datetime(2026, 8, 30, 8, 30, tzinfo=timezone.utc),
        speed_multiplier=speed,
        time_source=time_source,
    )


def test_initial_state_is_deterministic_simulated_and_synthetic() -> None:
    first = make_engine(FakeTimeSource()).snapshot()
    second = make_engine(FakeTimeSource()).snapshot()

    assert first == second
    assert first.lifecycle is SimulationLifecycle.READY
    assert first.data_provenance == "SIMULATED"
    assert first.patient.synthetic is True
    assert first.patient.patient_id == "DEMO-001"


def test_seed_derivation_is_deterministic_and_namespaced() -> None:
    first = make_engine(FakeTimeSource()).random_source
    second = make_engine(FakeTimeSource()).random_source

    assert first.derive_seed("future-module-a") == second.derive_seed("future-module-a")
    assert first.derive_seed("future-module-a") != first.derive_seed("future-module-b")


def test_start_pause_and_resume_lifecycle() -> None:
    engine = make_engine(FakeTimeSource())
    assert engine.start().lifecycle is SimulationLifecycle.RUNNING
    assert engine.pause().lifecycle is SimulationLifecycle.PAUSED
    assert engine.resume().lifecycle is SimulationLifecycle.RUNNING


def test_uninitialized_engine_requires_create_before_start() -> None:
    engine = DigitalPatientEngine(time_source=FakeTimeSource(), initialized=False)
    assert engine.snapshot().lifecycle is SimulationLifecycle.UNINITIALIZED

    with pytest.raises(SimulationLifecycleError):
        engine.start()

    assert engine.create().lifecycle is SimulationLifecycle.READY


def test_simulated_time_advances_at_configured_speed() -> None:
    time_source = FakeTimeSource()
    engine = make_engine(time_source, speed=3_600)
    initial = engine.snapshot().simulated_time

    engine.start()
    time_source.advance(2)

    assert engine.snapshot().simulated_time == initial + timedelta(hours=2)


def test_paused_time_is_frozen_and_resume_has_no_pause_jump() -> None:
    time_source = FakeTimeSource()
    engine = make_engine(time_source, speed=21_600)
    engine.start()
    time_source.advance(1)
    paused = engine.pause().simulated_time

    time_source.advance(5)
    assert engine.snapshot().simulated_time == paused

    engine.resume()
    assert engine.snapshot().simulated_time == paused
    time_source.advance(1)
    assert engine.snapshot().simulated_time == paused + timedelta(hours=6)


def test_reset_restores_start_time_seed_and_ready_state() -> None:
    time_source = FakeTimeSource()
    engine = make_engine(time_source, seed=99)
    initial = engine.snapshot()
    engine.start()
    time_source.advance(10)

    reset = engine.reset()

    assert reset.simulated_time == initial.simulated_time
    assert reset.seed == 99
    assert reset.lifecycle is SimulationLifecycle.READY


def test_reset_invokes_registered_runtime_hooks() -> None:
    engine = make_engine(FakeTimeSource())
    calls: list[str] = []
    engine.register_reset_hook(lambda: calls.append("reset"))

    engine.reset()

    assert calls == ["reset"]


def test_speed_change_has_no_discontinuity_and_applies_forward() -> None:
    time_source = FakeTimeSource()
    engine = make_engine(time_source, speed=21_600)
    engine.start()
    time_source.advance(1)
    before = engine.snapshot().simulated_time

    changed = engine.set_speed(3_600)
    assert changed.simulated_time == before

    time_source.advance(1)
    assert engine.snapshot().simulated_time == before + timedelta(hours=1)


@pytest.mark.parametrize("speed", [0, 86_401])
def test_invalid_speed_is_rejected(speed: float) -> None:
    with pytest.raises(SimulationValueError):
        make_engine(FakeTimeSource(), speed=speed)


def test_manual_step_is_exact_while_ready_and_paused() -> None:
    engine = make_engine(FakeTimeSource())
    initial = engine.snapshot().simulated_time
    assert engine.step(21_600).simulated_time == initial + timedelta(hours=6)

    engine.start()
    engine.pause()
    paused = engine.snapshot().simulated_time
    assert engine.step(60).simulated_time == paused + timedelta(minutes=1)


def test_manual_step_while_running_is_rejected() -> None:
    engine = make_engine(FakeTimeSource())
    engine.start()

    with pytest.raises(SimulationLifecycleError):
        engine.step(60)


@pytest.mark.parametrize(
    ("action", "expected_lifecycle"),
    [
        ("pause", SimulationLifecycle.READY),
        ("resume", SimulationLifecycle.READY),
        ("start_twice", SimulationLifecycle.RUNNING),
    ],
)
def test_invalid_lifecycle_transitions_are_rejected(
    action: str,
    expected_lifecycle: SimulationLifecycle,
) -> None:
    engine = make_engine(FakeTimeSource())
    if action == "start_twice":
        engine.start()
        operation = engine.start
    else:
        operation = getattr(engine, action)

    with pytest.raises(SimulationLifecycleError) as error:
        operation()

    assert error.value.lifecycle is expected_lifecycle


def test_clock_event_contains_no_medical_measurements() -> None:
    payload = make_engine(FakeTimeSource()).clock_event().model_dump()
    forbidden = {
        "bioimpedance",
        "imu",
        "temperature",
        "risk",
        "anomaly_score",
        "adi",
        "diagnosis",
    }
    assert forbidden.isdisjoint(payload)
