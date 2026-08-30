import math
from dataclasses import dataclass

from app.simulation.bioimpedance.models import ColeModelParameters


@dataclass(frozen=True)
class IdealImpedancePoint:
    frequency_hz: float
    impedance_ohm: complex


class ColeImpedanceModel:
    """Pure ideal model: Z = Rinf + (R0-Rinf)/(1+(jωτ)^β)."""

    def __init__(self, parameters: ColeModelParameters) -> None:
        self.parameters = parameters

    def impedance_at(self, frequency_hz: float) -> complex:
        if frequency_hz <= 0:
            raise ValueError("frequency_hz must be positive")
        angular_frequency_rad_s = 2 * math.pi * frequency_hz
        dispersion = (1j * angular_frequency_rad_s * self.parameters.tau_seconds) ** (
            self.parameters.beta
        )
        return self.parameters.r_infinity_ohm + (
            self.parameters.r_zero_ohm - self.parameters.r_infinity_ohm
        ) / (1 + dispersion)

    def sweep(self, frequencies_hz: list[float]) -> list[IdealImpedancePoint]:
        return [
            IdealImpedancePoint(
                frequency_hz=frequency_hz,
                impedance_ohm=self.impedance_at(frequency_hz),
            )
            for frequency_hz in frequencies_hz
        ]

