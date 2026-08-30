import math
import random
from typing import Protocol

from app.domain.enums import ArmSide
from app.simulation.random_source import SimulationRandom
from app.simulation.sensors.config import GRAVITY_M_S2
from app.simulation.sensors.models import ContactCondition, ContactSample, IMUSample, MotionCondition, TemperatureSample


def _times(duration: float, rate: float) -> list[float]:
    return [index / rate for index in range(round(duration * rate) + 1)]


class MotionSource(Protocol):
    def acquire_samples(self, *, arm_side: ArmSide, window_index: int, condition: MotionCondition, duration_seconds: float, sample_rate_hz: float) -> list[IMUSample]: ...


class TemperatureSource(Protocol):
    def acquire_samples(self, *, arm_side: ArmSide, window_index: int, offset_c: float, duration_seconds: float, sample_rate_hz: float) -> list[TemperatureSample]: ...


class ContactSource(Protocol):
    def acquire_samples(self, *, arm_side: ArmSide, window_index: int, condition: ContactCondition, duration_seconds: float, sample_rate_hz: float) -> list[ContactSample]: ...


class _NamespacedSource:
    def __init__(self, random_source: SimulationRandom) -> None:
        self._random_source = random_source

    def _rng(self, modality: str, arm: ArmSide, window: int) -> random.Random:
        return random.Random(self._random_source.derive_seed(f"{modality}.{arm.value.lower()}.window.{window}"))


class DigitalTwinMotionSource(_NamespacedSource):
    """x forward, y right, z up; gravity is projected into sensor axes."""
    def acquire_samples(self, *, arm_side: ArmSide, window_index: int, condition: MotionCondition, duration_seconds: float, sample_rate_hz: float) -> list[IMUSample]:
        rng = self._rng("imu", arm_side, window_index)
        side = 1.0 if arm_side is ArmSide.LEFT else -1.0
        base_roll, base_pitch, base_yaw = (2.0 * side, -3.0 + side, 5.0 * side)
        samples: list[IMUSample] = []
        for t in _times(duration_seconds, sample_rate_hz):
            if condition is MotionCondition.STABLE_REST:
                roll, pitch, yaw = base_roll + .10 * math.sin(2 * math.pi * .35 * t), base_pitch + .08 * math.sin(2 * math.pi * .25 * t), base_yaw
                gx, gy, gz = math.radians(.10 * 2 * math.pi * .35 * math.cos(2 * math.pi * .35 * t)), math.radians(.08 * 2 * math.pi * .25 * math.cos(2 * math.pi * .25 * t)), 0.0
                tx = ty = tz = 0.0
            elif condition is MotionCondition.ACTIVE_MOTION:
                roll, pitch, yaw = base_roll + 8 * math.sin(2 * math.pi * .8 * t), base_pitch + 10 * math.sin(2 * math.pi * .6 * t + .3), base_yaw + 6 * math.sin(2 * math.pi * .45 * t)
                gx, gy, gz = math.radians(8 * 2 * math.pi * .8 * math.cos(2 * math.pi * .8 * t)), math.radians(10 * 2 * math.pi * .6 * math.cos(2 * math.pi * .6 * t + .3)), math.radians(6 * 2 * math.pi * .45 * math.cos(2 * math.pi * .45 * t))
                tx, ty, tz = 1.1 * math.sin(2 * math.pi * 1.2 * t), .7 * math.cos(2 * math.pi * .9 * t + .2), .4 * math.sin(2 * math.pi * .65 * t)
            else:
                progress = .5 - .5 * math.cos(math.pi * t / duration_seconds)
                rate = .5 * math.pi / duration_seconds * math.sin(math.pi * t / duration_seconds)
                roll, pitch, yaw = base_roll + 30 * progress, base_pitch - 20 * progress, base_yaw + 15 * progress
                gx, gy, gz = math.radians(30 * rate), math.radians(-20 * rate), math.radians(15 * rate)
                tx = ty = tz = 0.0
            roll_r, pitch_r = math.radians(roll), math.radians(pitch)
            ax = -GRAVITY_M_S2 * math.sin(pitch_r) + tx + rng.uniform(-.025, .025)
            ay = GRAVITY_M_S2 * math.sin(roll_r) * math.cos(pitch_r) + ty + rng.uniform(-.025, .025)
            az = GRAVITY_M_S2 * math.cos(roll_r) * math.cos(pitch_r) + tz + rng.uniform(-.025, .025)
            samples.append(IMUSample(relative_time_seconds=t, acceleration_x_m_s2=ax, acceleration_y_m_s2=ay, acceleration_z_m_s2=az, angular_velocity_x_rad_s=gx + rng.uniform(-.002, .002), angular_velocity_y_rad_s=gy + rng.uniform(-.002, .002), angular_velocity_z_rad_s=gz + rng.uniform(-.002, .002), roll_deg=roll, pitch_deg=pitch, yaw_deg=yaw))
        return samples


class DigitalTwinTemperatureSource(_NamespacedSource):
    def acquire_samples(self, *, arm_side: ArmSide, window_index: int, offset_c: float, duration_seconds: float, sample_rate_hz: float) -> list[TemperatureSample]:
        rng = self._rng("temperature", arm_side, window_index)
        base = 33.2 if arm_side is ArmSide.LEFT else 33.0
        return [TemperatureSample(relative_time_seconds=t, temperature_c=base + offset_c + .025 * math.sin(2 * math.pi * .18 * t) + rng.uniform(-.01, .01)) for t in _times(duration_seconds, sample_rate_hz)]


class DigitalTwinContactSource(_NamespacedSource):
    def acquire_samples(self, *, arm_side: ArmSide, window_index: int, condition: ContactCondition, duration_seconds: float, sample_rate_hz: float) -> list[ContactSample]:
        rng = self._rng("contact", arm_side, window_index)
        base = 1200.0 if arm_side is ArmSide.LEFT else 1250.0
        if condition is ContactCondition.POOR_CONTACT:
            base += 3400.0; amplitude, noise = 260.0, 50.0
        elif condition is ContactCondition.UNSTABLE_CONTACT:
            amplitude, noise = 220.0, 60.0
        else:
            amplitude, noise = 35.0, 18.0
        return [ContactSample(relative_time_seconds=t, contact_impedance_ohm=base + amplitude * math.sin(2 * math.pi * 1.05 * t + .15) + rng.uniform(-noise, noise)) for t in _times(duration_seconds, sample_rate_hz)]
