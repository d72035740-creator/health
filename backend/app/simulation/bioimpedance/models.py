from enum import Enum
from typing import Annotated, Self

from pydantic import AwareDatetime, Field, model_validator

from app.domain.enums import ArmSide, DataProvenance
from app.domain.models import BioimpedanceSweep, ContractModel


class AcquisitionQualification(str, Enum):
    RAW_UNQUALIFIED = "RAW_UNQUALIFIED"


class BioimpedanceSourceType(str, Enum):
    DIGITAL_TWIN = "DIGITAL_TWIN"


class ColeModelParameters(ContractModel):
    """Synthetic Cole parameters; not clinical reference values."""

    r_zero_ohm: Annotated[float, Field(gt=0)]
    r_infinity_ohm: Annotated[float, Field(gt=0)]
    tau_seconds: Annotated[float, Field(gt=0)]
    beta: Annotated[float, Field(gt=0, le=1)]

    @model_validator(mode="after")
    def validate_resistance_asymptotes(self) -> Self:
        if self.r_zero_ohm <= self.r_infinity_ohm:
            raise ValueError("r_zero_ohm must be greater than r_infinity_ohm")
        return self


class FrequencyConfiguration(ContractModel):
    frequencies_hz: list[Annotated[float, Field(gt=0)]] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_ordered_unique_frequencies(self) -> Self:
        if len(set(self.frequencies_hz)) != len(self.frequencies_hz):
            raise ValueError("frequencies_hz must be unique")
        if self.frequencies_hz != sorted(self.frequencies_hz):
            raise ValueError("frequencies_hz must be ordered ascending")
        return self


class InstrumentationNoiseConfiguration(ContractModel):
    enabled: bool
    relative_bound: Annotated[float, Field(ge=0, le=0.01)]


class BioimpedanceTwinConfiguration(ContractModel):
    model_name: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    frequencies_hz: list[float]
    provenance: DataProvenance
    source: BioimpedanceSourceType
    qualification: AcquisitionQualification
    noise: InstrumentationNoiseConfiguration
    left_parameters: ColeModelParameters
    right_parameters: ColeModelParameters


class BilateralBioimpedanceSweep(ContractModel):
    pair_id: str = Field(min_length=1)
    sweep_index: Annotated[int, Field(ge=1)]
    simulation_id: str = Field(min_length=1)
    simulated_time: AwareDatetime
    wall_clock_time: AwareDatetime
    provenance: DataProvenance
    source: BioimpedanceSourceType
    qualification: AcquisitionQualification
    model_revision: str = Field(min_length=1)
    left: BioimpedanceSweep
    right: BioimpedanceSweep

    @model_validator(mode="after")
    def validate_bilateral_alignment(self) -> Self:
        if self.left.arm_side is not ArmSide.LEFT or self.right.arm_side is not ArmSide.RIGHT:
            raise ValueError("bilateral sweep arm labels are invalid")
        left_frequencies = [point.frequency_hz for point in self.left.points]
        right_frequencies = [point.frequency_hz for point in self.right.points]
        if left_frequencies != right_frequencies:
            raise ValueError("bilateral sweep frequencies must match")
        for sweep in (self.left, self.right):
            if sweep.wall_clock_time != self.wall_clock_time:
                raise ValueError("arm and pair wall_clock_time must match")
            if sweep.simulated_time != self.simulated_time:
                raise ValueError("arm and pair simulated_time must match")
            if sweep.provenance is not self.provenance:
                raise ValueError("arm and pair provenance must match")
        return self

