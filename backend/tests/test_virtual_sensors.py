import math
import random
from datetime import datetime, timezone

import pytest

from app.domain.enums import SimulationLifecycle
from app.simulation.bioimpedance.service import BilateralBioimpedanceService
from app.simulation.engine import DigitalPatientEngine
from app.simulation.sensors.models import ContactCondition, MotionCondition, SensorWindowRequest
from app.simulation.sensors.service import VirtualSensorsUnavailableError, WearableSensorService
from app.simulation.time_source import TimeSource


class FixedTimeSource(TimeSource):
    def monotonic(self) -> float: return 10.0
    def wall_clock_time(self) -> datetime: return datetime(2026, 8, 30, 12, 0, tzinfo=timezone.utc)


def build_service(initialized: bool = True) -> tuple[DigitalPatientEngine, WearableSensorService]:
    engine = DigitalPatientEngine(seed=42_017, time_source=FixedTimeSource(), initialized=initialized)
    return engine, WearableSensorService(engine=engine)


def test_window_is_synchronized_local_time_and_does_not_advance_engine() -> None:
    engine, service = build_service(); before = engine.snapshot(); window = service.acquire(SensorWindowRequest())
    after = engine.snapshot()
    assert after.simulated_time == before.simulated_time
    assert window.left.arm_side == "LEFT" and window.right.arm_side == "RIGHT"
    assert window.anchor_simulated_time == before.simulated_time
    assert window.qualification == "RAW_UNQUALIFIED" and window.provenance == "SIMULATED"
    for band, rate, samples in ((window.left, 50, window.left.imu_samples), (window.left, 4, window.left.temperature_samples), (window.left, 12, window.left.contact_samples)):
        assert samples[0].relative_time_seconds == 0
        assert samples[-1].relative_time_seconds == window.duration_seconds
        assert all(b.relative_time_seconds - a.relative_time_seconds == pytest.approx(1 / rate) for a, b in zip(samples, samples[1:]))


def test_imu_is_gravity_coherent_and_presets_change_motion() -> None:
    engine, service = build_service()
    stable = service.acquire(SensorWindowRequest())
    active = service.acquire(SensorWindowRequest(motion_condition=MotionCondition.ACTIVE_MOTION))
    posture = service.acquire(SensorWindowRequest(motion_condition=MotionCondition.POSTURE_TRANSITION))
    stable_mag = [math.sqrt(s.acceleration_x_m_s2**2+s.acceleration_y_m_s2**2+s.acceleration_z_m_s2**2) for s in stable.left.imu_samples]
    assert sum(stable_mag) / len(stable_mag) == pytest.approx(9.80665, abs=.12)
    assert max(abs(s.angular_velocity_x_rad_s) for s in stable.left.imu_samples) < .02
    assert max(abs(s.angular_velocity_x_rad_s) for s in active.left.imu_samples) > .3
    assert posture.left.imu_samples[0].roll_deg != posture.left.imu_samples[-1].roll_deg
    assert max(abs(s.angular_velocity_x_rad_s) for s in posture.left.imu_samples) > .1
    assert active.left.imu_samples != active.right.imu_samples


def test_temperature_and_contact_are_raw_and_conditioned() -> None:
    _, service = build_service()
    baseline = service.acquire(SensorWindowRequest())
    warmer = service.acquire(SensorWindowRequest(temperature_offset_c=1.0, contact_condition=ContactCondition.POOR_CONTACT))
    assert warmer.left.temperature_samples[0].temperature_c - baseline.left.temperature_samples[0].temperature_c == pytest.approx(1, abs=.05)
    assert min(s.contact_impedance_ohm for s in warmer.left.contact_samples) > max(s.contact_impedance_ohm for s in baseline.left.contact_samples)
    assert "quality" not in warmer.model_dump_json().lower()


def test_reset_rng_and_bis_activity_do_not_perturb_sensor_stream() -> None:
    engine, service = build_service(); first = service.acquire(SensorWindowRequest())
    _ = [random.random() for _ in range(1000)]; engine.reset(); repeated = service.acquire(SensorWindowRequest())
    assert repeated == first
    engine.reset(); before_bis = service.acquire(SensorWindowRequest())
    engine.reset(); BilateralBioimpedanceService(engine=engine).acquire(); after_bis = service.acquire(SensorWindowRequest())
    assert after_bis == before_bis


def test_uninitialized_engine_rejects_windows() -> None:
    engine, service = build_service(False)
    assert engine.snapshot().lifecycle is SimulationLifecycle.UNINITIALIZED
    with pytest.raises(VirtualSensorsUnavailableError): service.acquire(SensorWindowRequest())
