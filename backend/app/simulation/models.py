from typing import Annotated, Literal

from pydantic import AwareDatetime, Field

from app.domain.enums import ArmSide, DataProvenance, SimulationLifecycle
from app.domain.models import ContractModel


MIN_SPEED_MULTIPLIER = 0.1
MAX_SPEED_MULTIPLIER = 86_400.0
MAX_MANUAL_STEP_SECONDS = 31_536_000.0

SpeedMultiplier = Annotated[
    float,
    Field(ge=MIN_SPEED_MULTIPLIER, le=MAX_SPEED_MULTIPLIER),
]


class SyntheticPatient(ContractModel):
    """Fictional identity for local simulation; never a clinical record."""

    patient_id: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    age_years: Annotated[int, Field(ge=18, le=120)]
    sex: Literal["FEMALE", "MALE", "OTHER", "UNSPECIFIED"]
    dominant_arm: ArmSide
    created_at: AwareDatetime
    synthetic: Literal[True] = True


class SimulationSnapshot(ContractModel):
    simulation_id: str = Field(min_length=1)
    patient: SyntheticPatient
    seed: int
    lifecycle: SimulationLifecycle
    wall_clock_time: AwareDatetime
    simulated_time: AwareDatetime
    speed_multiplier: SpeedMultiplier
    data_provenance: Literal[DataProvenance.SIMULATED] = DataProvenance.SIMULATED


class SimulationClockEvent(ContractModel):
    type: Literal["simulation.clock"] = "simulation.clock"
    simulation_id: str = Field(min_length=1)
    lifecycle: SimulationLifecycle
    wall_clock_time: AwareDatetime
    simulated_time: AwareDatetime
    speed_multiplier: SpeedMultiplier


class SpeedUpdate(ContractModel):
    speed_multiplier: SpeedMultiplier


class ManualStepRequest(ContractModel):
    seconds: Annotated[float, Field(gt=0, le=MAX_MANUAL_STEP_SECONDS)]

