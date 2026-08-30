from math import isclose
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from app.domain.enums import (
    ArmSide,
    DataProvenance,
    PrototypeMode,
    SubsystemStatus,
    SurveillanceState,
)


PositiveFloat = Annotated[float, Field(gt=0)]
QualityScore = Annotated[float, Field(ge=0, le=1)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SimulationClock(ContractModel):
    """Explicit wall-clock and accelerated simulated-time context."""

    simulation_id: str = Field(min_length=1)
    seed: int
    wall_clock_time: AwareDatetime
    simulated_time: AwareDatetime
    speed_multiplier: PositiveFloat
    running: bool


class RawSample(ContractModel):
    sample_id: str = Field(min_length=1)
    arm_side: ArmSide
    provenance: DataProvenance
    wall_clock_time: AwareDatetime
    simulated_time: AwareDatetime | None = None


class IMUSample(RawSample):
    acceleration_x_m_s2: float
    acceleration_y_m_s2: float
    acceleration_z_m_s2: float
    angular_velocity_x_rad_s: float
    angular_velocity_y_rad_s: float
    angular_velocity_z_rad_s: float


class TemperatureSample(RawSample):
    temperature_c: float


class ContactQualitySample(RawSample):
    contact_quality_score: QualityScore


class BioimpedanceFrequencyPoint(ContractModel):
    frequency_hz: PositiveFloat
    resistance_ohm: float
    reactance_ohm: float
    magnitude_ohm: Annotated[float, Field(ge=0)]
    phase_deg: Annotated[float, Field(ge=-180, le=180)]

    @model_validator(mode="after")
    def magnitude_matches_components(self) -> "BioimpedanceFrequencyPoint":
        expected = (self.resistance_ohm**2 + self.reactance_ohm**2) ** 0.5
        if not isclose(self.magnitude_ohm, expected, rel_tol=0.02, abs_tol=0.01):
            raise ValueError("magnitude_ohm must match resistance/reactance components")
        return self


class BioimpedanceSweep(RawSample):
    points: list[BioimpedanceFrequencyPoint] = Field(min_length=1)


class SensorFrame(ContractModel):
    frame_id: str = Field(min_length=1)
    arm_side: ArmSide
    provenance: DataProvenance
    clock: SimulationClock | None = None
    bioimpedance: BioimpedanceSweep | None = None
    imu: IMUSample | None = None
    temperature: TemperatureSample | None = None
    contact_quality: ContactQualitySample | None = None


class MeasurementQualityAssessment(ContractModel):
    frame_id: str = Field(min_length=1)
    status: SubsystemStatus
    overall_quality_score: QualityScore | None = None
    reasons: list[str] = Field(default_factory=list)


class ProcessedFeatureVector(ContractModel):
    frame_id: str = Field(min_length=1)
    status: SubsystemStatus
    features: dict[str, float] | None = None
    units: dict[str, str] | None = None


class BaselineSnapshot(ContractModel):
    arm_side: ArmSide
    status: SubsystemStatus
    established_at: AwareDatetime | None = None
    feature_baselines: dict[str, float] | None = None


class MLInferenceResult(ContractModel):
    frame_id: str = Field(min_length=1)
    status: SubsystemStatus
    anomaly_score: QualityScore | None = None
    model_version: str | None = None


class TemporalAssessment(ContractModel):
    frame_id: str = Field(min_length=1)
    status: SubsystemStatus
    persistence_score: float | None = None
    explanation: str | None = None


class ConfounderAssessment(ContractModel):
    frame_id: str = Field(min_length=1)
    status: SubsystemStatus
    identified_confounders: list[str] | None = None
    explanation: str | None = None


class DecisionSnapshot(ContractModel):
    frame_id: str = Field(min_length=1)
    status: SubsystemStatus
    surveillance_state: SurveillanceState | None = None
    differential_index: float | None = None
    explanation: str | None = None


class TimelineEvent(ContractModel):
    event_id: str = Field(min_length=1)
    wall_clock_time: AwareDatetime
    simulated_time: AwareDatetime | None = None
    event_type: str = Field(min_length=1)
    message: str = Field(min_length=1)
    provenance: DataProvenance | None = None


class SystemStatus(ContractModel):
    prototype_mode: PrototypeMode
    data_provenance: DataProvenance
    backend: SubsystemStatus
    digital_patient_engine: SubsystemStatus
    digital_twin: SubsystemStatus
    bioimpedance_digital_twin: SubsystemStatus
    virtual_imu: SubsystemStatus
    virtual_temperature: SubsystemStatus
    virtual_contact: SubsystemStatus
    quality_engine: SubsystemStatus
    signal_processing: SubsystemStatus
    baseline_engine: SubsystemStatus
    ml_engine: SubsystemStatus
    temporal_engine: SubsystemStatus
    confounder_engine: SubsystemStatus
    decision_engine: SubsystemStatus


class SystemHeartbeat(ContractModel):
    type: Literal["system.heartbeat"] = "system.heartbeat"
    timestamp: AwareDatetime
    backend_status: SubsystemStatus
