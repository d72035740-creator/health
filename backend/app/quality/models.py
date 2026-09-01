from enum import Enum
from typing import Annotated
from pydantic import AwareDatetime, Field, model_validator
from app.domain.enums import DataProvenance
from app.domain.models import ContractModel
from app.simulation.sensors.models import SensorWindowRequest, WearableSensorWindow
from app.simulation.bioimpedance.models import BilateralBioimpedanceSweep
from app.signal_processing.models import ProcessedBioimpedanceFeatures
from app.baseline.models import BaselineComparison
from app.ml.models import MLInferenceResult
from app.temporal.models import TemporalAssessment
from app.confounders.models import ConfounderAssessment
from app.decision.models import DecisionSnapshot

Score = Annotated[float, Field(ge=0, le=100)]

class MeasurementQualification(str, Enum):
    QUALIFIED = "QUALIFIED"
    REJECTED = "REJECTED"

class RejectionReason(str, Enum):
    HIGH_MOTION = "HIGH_MOTION"
    POSTURE_UNSTABLE = "POSTURE_UNSTABLE"
    CONTACT_UNSTABLE = "CONTACT_UNSTABLE"
    CONTACT_IMPEDANCE_HIGH = "CONTACT_IMPEDANCE_HIGH"
    TEMPERATURE_UNSTABLE = "TEMPERATURE_UNSTABLE"
    STRUCTURAL_INTEGRITY_FAILURE = "STRUCTURAL_INTEGRITY_FAILURE"
    NON_FINITE_SENSOR_DATA = "NON_FINITE_SENSOR_DATA"
    INSUFFICIENT_SAMPLES = "INSUFFICIENT_SAMPLES"

class QualityDimensionScores(ContractModel):
    motion_score: Score
    posture_score: Score
    contact_score: Score
    temperature_score: Score
    integrity_score: Score

class QualityFeatureSummary(ContractModel):
    acceleration_mean_m_s2: float
    acceleration_sd_m_s2: float
    acceleration_range_m_s2: float
    gyro_rms_rad_s: float
    gyro_sd_rad_s: float
    gyro_max_rad_s: float
    roll_drift_deg: float
    pitch_drift_deg: float
    yaw_drift_deg: float
    contact_mean_ohm: float
    contact_median_ohm: float
    contact_sd_ohm: float
    contact_cv: float
    contact_range_ohm: float
    temperature_mean_c: float
    temperature_sd_c: float
    temperature_range_c: float
    temperature_drift_c: float

class MeasurementQualityAssessment(ContractModel):
    window_id: str
    window_index: int
    provenance: DataProvenance
    qualification: MeasurementQualification
    overall_score: Score
    dimension_scores: QualityDimensionScores
    feature_summary: dict[str, QualityFeatureSummary]
    rejection_reasons: list[RejectionReason] = Field(default_factory=list)
    evaluated_at: AwareDatetime
    quality_engine_name: str
    threshold_revision: str
    explanation: str

class MeasurementAttempt(ContractModel):
    attempt_id: str
    attempt_index: int
    simulated_time: AwareDatetime
    sensor_window: WearableSensorWindow
    quality_assessment: MeasurementQualityAssessment
    bis_sweep: BilateralBioimpedanceSweep | None = None
    processed_features: ProcessedBioimpedanceFeatures | None = None
    baseline_comparison: BaselineComparison | None = None
    ml_inference: MLInferenceResult | None = None
    temporal_assessment: TemporalAssessment | None = None
    confounder_assessment: ConfounderAssessment | None = None
    decision_snapshot: DecisionSnapshot | None = None

    @model_validator(mode="after")
    def validate_gating(self) -> "MeasurementAttempt":
        qualified = self.quality_assessment.qualification is MeasurementQualification.QUALIFIED
        if qualified != (self.bis_sweep is not None):
            raise ValueError("qualified attempts require BIS; rejected attempts must not contain BIS")
        if qualified != (self.processed_features is not None):
            raise ValueError("qualified attempts require processed features; rejected attempts must not contain them")
        if not qualified and self.baseline_comparison is not None:
            raise ValueError("rejected attempts must not contain baseline comparison")
        if not qualified and self.ml_inference is not None:
            raise ValueError("rejected attempts must not contain ML inference")
        if not qualified and (self.temporal_assessment is not None or self.confounder_assessment is not None):
            raise ValueError("rejected attempts must not contain temporal/confounder evidence")
        if not qualified and self.decision_snapshot is not None:
            raise ValueError("rejected attempts must not contain cycle decision")
        return self
