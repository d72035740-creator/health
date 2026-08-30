import math
import random
from datetime import datetime, timezone

import pytest

from app.domain.enums import ArmSide, SimulationLifecycle
from app.simulation.bioimpedance.cole import ColeImpedanceModel
from app.simulation.bioimpedance.config import (
    DEFAULT_FREQUENCIES,
    LEFT_ARM_PARAMETERS,
    default_configuration,
)
from app.simulation.bioimpedance.models import (
    AcquisitionQualification,
    InstrumentationNoiseConfiguration,
)
from app.simulation.bioimpedance.service import (
    BilateralBioimpedanceService,
    BioimpedanceUnavailableError,
)
from app.simulation.engine import DigitalPatientEngine
from app.simulation.time_source import TimeSource


class FixedTimeSource(TimeSource):
    def monotonic(self) -> float:
        return 10.0

    def wall_clock_time(self) -> datetime:
        return datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def build_service(
    *,
    noise_enabled: bool = True,
    seed: int = 42_017,
    initialized: bool = True,
) -> tuple[DigitalPatientEngine, BilateralBioimpedanceService]:
    engine = DigitalPatientEngine(
        seed=seed,
        time_source=FixedTimeSource(),
        initialized=initialized,
    )
    noise = InstrumentationNoiseConfiguration(
        enabled=noise_enabled,
        relative_bound=0.0015,
    )
    service = BilateralBioimpedanceService(
        engine=engine,
        configuration=default_configuration(noise=noise),
    )
    return engine, service


def point_values(sweep: object) -> list[tuple[float, float, float, float, float]]:
    return [
        (
            point.frequency_hz,
            point.resistance_ohm,
            point.reactance_ohm,
            point.magnitude_ohm,
            point.phase_deg,
        )
        for point in sweep.points  # type: ignore[attr-defined]
    ]


def test_bilateral_acquisition_is_synchronized_raw_and_simulated() -> None:
    _, service = build_service()
    pair = service.acquire()

    assert pair.sweep_index == 1
    assert pair.left.arm_side is ArmSide.LEFT
    assert pair.right.arm_side is ArmSide.RIGHT
    assert pair.left.wall_clock_time == pair.right.wall_clock_time == pair.wall_clock_time
    assert pair.left.simulated_time == pair.right.simulated_time == pair.simulated_time
    assert pair.provenance == "SIMULATED"
    assert pair.qualification is AcquisitionQualification.RAW_UNQUALIFIED
    assert [p.frequency_hz for p in pair.left.points] == [
        p.frequency_hz for p in pair.right.points
    ]


def test_synthetic_arms_are_similar_but_not_identical() -> None:
    _, service = build_service(noise_enabled=False)
    pair = service.acquire()
    left = [point.magnitude_ohm for point in pair.left.points]
    right = [point.magnitude_ohm for point in pair.right.points]

    assert left != right
    assert all(abs(a - b) / ((a + b) / 2) < 0.05 for a, b in zip(left, right, strict=True))


def test_noise_disabled_matches_ideal_model_exactly() -> None:
    _, service = build_service(noise_enabled=False)
    acquired = service.acquire().left.points
    ideal = ColeImpedanceModel(LEFT_ARM_PARAMETERS).sweep(DEFAULT_FREQUENCIES.frequencies_hz)

    for actual, expected in zip(acquired, ideal, strict=True):
        assert actual.resistance_ohm == pytest.approx(expected.impedance_ohm.real)
        assert actual.reactance_ohm == pytest.approx(expected.impedance_ohm.imag)


def test_noise_output_remains_derived_from_same_complex_impedance() -> None:
    _, service = build_service(noise_enabled=True)
    pair = service.acquire()
    for point in [*pair.left.points, *pair.right.points]:
        assert point.magnitude_ohm == pytest.approx(
            math.sqrt(point.resistance_ohm**2 + point.reactance_ohm**2)
        )
        assert point.phase_deg == pytest.approx(
            math.degrees(math.atan2(point.reactance_ohm, point.resistance_ohm))
        )


def test_reset_reproduces_first_noisy_sweep_and_pair_identity() -> None:
    engine, service = build_service(noise_enabled=True)
    first = service.acquire()
    service.acquire()

    engine.reset()
    repeated = service.acquire()

    assert repeated == first


def test_repeated_noisy_sweeps_differ() -> None:
    _, service = build_service(noise_enabled=True)
    first = service.acquire()
    second = service.acquire()
    assert point_values(first.left) != point_values(second.left)
    assert first.pair_id != second.pair_id


def test_global_random_activity_does_not_change_bis_results() -> None:
    _, first_service = build_service(noise_enabled=True)
    first = first_service.acquire()

    random.seed(123456)
    _ = [random.random() for _ in range(1_000)]

    _, second_service = build_service(noise_enabled=True)
    second = second_service.acquire()
    assert second == first


def test_many_acquisitions_remain_finite() -> None:
    _, service = build_service(noise_enabled=True)
    for _ in range(100):
        pair = service.acquire()
        for point in [*pair.left.points, *pair.right.points]:
            assert all(
                math.isfinite(value)
                for value in (
                    point.resistance_ohm,
                    point.reactance_ohm,
                    point.magnitude_ohm,
                    point.phase_deg,
                )
            )


def test_acquisition_is_available_in_ready_running_and_paused() -> None:
    engine, service = build_service()
    assert engine.snapshot().lifecycle is SimulationLifecycle.READY
    service.acquire()
    engine.start()
    service.acquire()
    engine.pause()
    service.acquire()


def test_uninitialized_simulation_is_rejected() -> None:
    _, service = build_service(initialized=False)
    with pytest.raises(BioimpedanceUnavailableError):
        service.acquire()

