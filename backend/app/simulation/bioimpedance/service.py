from threading import RLock

from app.domain.enums import ArmSide, DataProvenance, SimulationLifecycle
from app.domain.interfaces import BioimpedanceSource
from app.simulation.bioimpedance.cole import ColeImpedanceModel
from app.simulation.bioimpedance.config import default_configuration
from app.simulation.bioimpedance.models import (
    AcquisitionQualification,
    BioimpedanceSourceType,
    BioimpedanceTwinConfiguration,
    BilateralBioimpedanceSweep,
)
from app.simulation.bioimpedance.source import DigitalTwinBioimpedanceSource
from app.simulation.engine import DigitalPatientEngine, simulation_engine


class BioimpedanceUnavailableError(RuntimeError):
    pass


class BilateralBioimpedanceService:
    def __init__(
        self,
        *,
        engine: DigitalPatientEngine,
        configuration: BioimpedanceTwinConfiguration | None = None,
        left_source: BioimpedanceSource | None = None,
        right_source: BioimpedanceSource | None = None,
    ) -> None:
        self._lock = RLock()
        self._engine = engine
        self._configuration = configuration or default_configuration()
        self._left_source = left_source or DigitalTwinBioimpedanceSource(
            arm_side=ArmSide.LEFT,
            model=ColeImpedanceModel(self._configuration.left_parameters),
            frequencies_hz=self._configuration.frequencies_hz,
            noise_configuration=self._configuration.noise,
            random_source=engine.random_source,
        )
        self._right_source = right_source or DigitalTwinBioimpedanceSource(
            arm_side=ArmSide.RIGHT,
            model=ColeImpedanceModel(self._configuration.right_parameters),
            frequencies_hz=self._configuration.frequencies_hz,
            noise_configuration=self._configuration.noise,
            random_source=engine.random_source,
        )
        self._sweep_index = 0
        engine.register_reset_hook(self.reset)

    def configuration(self) -> BioimpedanceTwinConfiguration:
        return self._configuration

    def reset(self) -> None:
        with self._lock:
            self._sweep_index = 0

    def acquire(self) -> BilateralBioimpedanceSweep:
        snapshot = self._engine.snapshot()
        if snapshot.lifecycle is SimulationLifecycle.UNINITIALIZED:
            raise BioimpedanceUnavailableError("Digital Patient simulation is uninitialized")

        with self._lock:
            self._sweep_index += 1
            sweep_index = self._sweep_index
            context = {
                "simulation_id": snapshot.simulation_id,
                "sweep_index": sweep_index,
                "wall_clock_time": snapshot.wall_clock_time,
                "simulated_time": snapshot.simulated_time,
            }
            left = self._left_source.acquire_sweep(arm_side=ArmSide.LEFT, **context)
            right = self._right_source.acquire_sweep(arm_side=ArmSide.RIGHT, **context)
            return BilateralBioimpedanceSweep(
                pair_id=f"{snapshot.simulation_id}:bis-pair:{sweep_index}",
                sweep_index=sweep_index,
                simulation_id=snapshot.simulation_id,
                simulated_time=snapshot.simulated_time,
                wall_clock_time=snapshot.wall_clock_time,
                provenance=DataProvenance.SIMULATED,
                source=BioimpedanceSourceType.DIGITAL_TWIN,
                qualification=AcquisitionQualification.RAW_UNQUALIFIED,
                model_revision=self._configuration.model_revision,
                left=left,
                right=right,
            )


bioimpedance_service = BilateralBioimpedanceService(engine=simulation_engine)

