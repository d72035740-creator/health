import random

from app.simulation.bioimpedance.models import InstrumentationNoiseConfiguration


class BoundedComplexInstrumentationNoise:
    """Small synthetic noise, not derived from final wearable characterization."""

    def __init__(self, configuration: InstrumentationNoiseConfiguration) -> None:
        self.configuration = configuration

    def apply(self, impedance_ohm: complex, *, rng: random.Random) -> complex:
        if not self.configuration.enabled or self.configuration.relative_bound == 0:
            return impedance_ohm
        bound = self.configuration.relative_bound
        resistance_scale = 1 + rng.uniform(-bound, bound)
        reactance_scale = 1 + rng.uniform(-bound, bound)
        return complex(
            impedance_ohm.real * resistance_scale,
            impedance_ohm.imag * reactance_scale,
        )

