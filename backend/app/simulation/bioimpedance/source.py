import math
import random
from datetime import datetime

from app.domain.enums import ArmSide, DataProvenance
from app.domain.models import BioimpedanceFrequencyPoint, BioimpedanceSweep
from app.simulation.bioimpedance.cole import ColeImpedanceModel
from app.simulation.bioimpedance.models import InstrumentationNoiseConfiguration
from app.simulation.bioimpedance.noise import BoundedComplexInstrumentationNoise
from app.simulation.random_source import SimulationRandom
from collections.abc import Callable


class DigitalTwinBioimpedanceSource:
    def __init__(
        self,
        *,
        arm_side: ArmSide,
        model: ColeImpedanceModel,
        frequencies_hz: list[float],
        noise_configuration: InstrumentationNoiseConfiguration,
        random_source: SimulationRandom,
        parameter_provider: Callable[[ArmSide, datetime, object], object] | None = None,
    ) -> None:
        self._arm_side = arm_side
        self._model = model
        self._frequencies_hz = frequencies_hz
        self._noise = BoundedComplexInstrumentationNoise(noise_configuration)
        self._random_source = random_source
        self._parameter_provider = parameter_provider

    def acquire_sweep(
        self,
        *,
        arm_side: ArmSide,
        simulation_id: str,
        sweep_index: int,
        wall_clock_time: datetime,
        simulated_time: datetime,
    ) -> BioimpedanceSweep:
        if arm_side is not self._arm_side:
            raise ValueError(f"source configured for {self._arm_side.value}, not {arm_side.value}")
        namespace = f"bioimpedance.{arm_side.value.lower()}.sweep.{sweep_index}"
        rng = random.Random(self._random_source.derive_seed(namespace))
        points: list[BioimpedanceFrequencyPoint] = []
        model = self._model
        if self._parameter_provider is not None:
            model = ColeImpedanceModel(self._parameter_provider(arm_side, simulated_time, self._model.parameters))
        for ideal in model.sweep(self._frequencies_hz):
            acquired = self._noise.apply(ideal.impedance_ohm, rng=rng)
            points.append(
                BioimpedanceFrequencyPoint(
                    frequency_hz=ideal.frequency_hz,
                    resistance_ohm=acquired.real,
                    reactance_ohm=acquired.imag,
                    magnitude_ohm=abs(acquired),
                    phase_deg=math.degrees(math.atan2(acquired.imag, acquired.real)),
                )
            )
        return BioimpedanceSweep(
            sample_id=f"{simulation_id}:bis:{arm_side.value.lower()}:{sweep_index}",
            arm_side=arm_side,
            provenance=DataProvenance.SIMULATED,
            wall_clock_time=wall_clock_time,
            simulated_time=simulated_time,
            points=points,
        )
