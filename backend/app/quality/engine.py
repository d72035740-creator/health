import math
from datetime import datetime, timezone
from statistics import mean
from app.domain.enums import DataProvenance
from app.quality.config import DEFAULT_THRESHOLDS, QUALITY_ENGINE_NAME, THRESHOLD_REVISION, QualityThresholdConfig
from app.quality.features import extract_features
from app.quality.models import MeasurementQualification, MeasurementQualityAssessment, QualityDimensionScores, QualityFeatureSummary, RejectionReason
from app.simulation.sensors.models import WearableSensorWindow

def _score(value: float, limit: float) -> float: return max(0.0, min(100.0, 100.0 * (1.0 - max(0.0, value) / limit)))
def _worst(features: dict[str, dict[str,float]], key: str, limit: float) -> float: return min(_score(f[key], limit) for f in features.values())

class MeasurementQualityEngine:
    def __init__(self, thresholds: QualityThresholdConfig = DEFAULT_THRESHOLDS) -> None: self.thresholds = thresholds
    def evaluate(self, window: WearableSensorWindow) -> MeasurementQualityAssessment:
        reasons: list[RejectionReason] = []; integrity = 100.0
        try:
            if window.left.arm_side.value != "LEFT" or window.right.arm_side.value != "RIGHT": raise ValueError("bilateral structure")
            if window.left.imu_sample_rate_hz <= 0 or window.right.imu_sample_rate_hz <= 0: raise ValueError("metadata")
            if any(len(x.imu_samples) < self.thresholds.minimum_samples or len(x.temperature_samples) < self.thresholds.minimum_samples or len(x.contact_samples) < self.thresholds.minimum_samples for x in (window.left,window.right)): reasons.append(RejectionReason.INSUFFICIENT_SAMPLES)
            features = extract_features(window)
        except FloatingPointError: features = {"LEFT": {}, "RIGHT": {}}; reasons.append(RejectionReason.NON_FINITE_SENSOR_DATA); integrity = 0.0
        except (ValueError, KeyError, AttributeError): features = {"LEFT": {}, "RIGHT": {}}; reasons.append(RejectionReason.STRUCTURAL_INTEGRITY_FAILURE); integrity = 0.0
        if features["LEFT"]:
            t=self.thresholds
            motion = min(_worst(features,"acceleration_sd_m_s2",t.motion_acceleration_sd_m_s2), _worst(features,"gyro_rms_rad_s",t.motion_gyro_rms_rad_s), _worst(features,"gyro_max_rad_s",t.motion_gyro_max_rad_s))
            posture = min(_worst(features,"roll_drift_deg",t.posture_drift_deg), _worst(features,"pitch_drift_deg",t.posture_drift_deg), _worst(features,"yaw_drift_deg",t.posture_drift_deg))
            contact = min(_worst(features,"contact_cv",t.contact_cv), _worst(features,"contact_range_ohm",t.contact_range_ohm), _worst(features,"contact_median_ohm",t.contact_median_max_ohm))
            temperature = min(_worst(features,"temperature_sd_c",t.temperature_sd_c), _worst(features,"temperature_range_c",t.temperature_range_c), _worst(features,"temperature_drift_c",t.temperature_drift_c))
            if motion < 45: reasons.append(RejectionReason.HIGH_MOTION)
            if posture < 45: reasons.append(RejectionReason.POSTURE_UNSTABLE)
            if contact < 45: reasons.append(RejectionReason.CONTACT_UNSTABLE)
            if any(f["contact_median_ohm"] > t.contact_median_max_ohm for f in features.values()): reasons.append(RejectionReason.CONTACT_IMPEDANCE_HIGH)
            if temperature < 45: reasons.append(RejectionReason.TEMPERATURE_UNSTABLE)
        else: motion = posture = contact = temperature = 0.0
        scores=QualityDimensionScores(motion_score=motion, posture_score=posture, contact_score=contact, temperature_score=temperature, integrity_score=integrity)
        overall=sum(score*weight for score,weight in zip([motion,posture,contact,temperature,integrity], self.thresholds.weights.values(), strict=True))
        if integrity < 100: reasons.append(RejectionReason.STRUCTURAL_INTEGRITY_FAILURE)
        qualified = not reasons and overall >= self.thresholds.overall_threshold and min(motion,contact,integrity) >= self.thresholds.critical_minimum
        summary={arm:QualityFeatureSummary(**vals) for arm,vals in features.items()} if features["LEFT"] else {}
        return MeasurementQualityAssessment(window_id=window.window_id, window_index=window.window_index, provenance=DataProvenance.SIMULATED, qualification=MeasurementQualification.QUALIFIED if qualified else MeasurementQualification.REJECTED, overall_score=overall, dimension_scores=scores, feature_summary=summary, rejection_reasons=list(dict.fromkeys(reasons)), evaluated_at=window.anchor_wall_clock_time, quality_engine_name=QUALITY_ENGINE_NAME, threshold_revision=THRESHOLD_REVISION, explanation="Technical acquisition conditions passed prototype engineering thresholds." if qualified else "Technical acquisition rejected; inspect the listed raw-sensor reasons.")

quality_engine = MeasurementQualityEngine()
