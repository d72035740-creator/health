from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.domain.models import BioimpedanceFrequencyPoint, IMUSample, SimulationClock


NOW = datetime.now(timezone.utc)


def test_imu_rejects_invalid_arm_enum() -> None:
    with pytest.raises(ValidationError):
        IMUSample(
            sample_id="imu-1",
            arm_side="CENTER",
            provenance="SIMULATED",
            wall_clock_time=NOW,
            simulated_time=NOW,
            acceleration_x_m_s2=0,
            acceleration_y_m_s2=0,
            acceleration_z_m_s2=9.81,
            angular_velocity_x_rad_s=0,
            angular_velocity_y_rad_s=0,
            angular_velocity_z_rad_s=0,
        )


def test_frequency_point_requires_positive_frequency() -> None:
    with pytest.raises(ValidationError):
        BioimpedanceFrequencyPoint(
            frequency_hz=0,
            resistance_ohm=3,
            reactance_ohm=4,
            magnitude_ohm=5,
            phase_deg=53.13,
        )


def test_frequency_point_rejects_inconsistent_magnitude() -> None:
    with pytest.raises(ValidationError):
        BioimpedanceFrequencyPoint(
            frequency_hz=5000,
            resistance_ohm=3,
            reactance_ohm=4,
            magnitude_ohm=20,
            phase_deg=53.13,
        )


def test_simulation_clock_requires_positive_speed() -> None:
    with pytest.raises(ValidationError):
        SimulationClock(
            simulation_id="sim-1",
            seed=42,
            wall_clock_time=NOW,
            simulated_time=NOW,
            speed_multiplier=0,
            running=False,
        )


def test_simulation_clock_rejects_timezone_naive_timestamps() -> None:
    with pytest.raises(ValidationError):
        SimulationClock(
            simulation_id="sim-1",
            seed=42,
            wall_clock_time=datetime.now(),
            simulated_time=NOW,
            speed_multiplier=1,
            running=False,
        )
