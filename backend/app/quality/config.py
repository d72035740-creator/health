from dataclasses import dataclass

QUALITY_ENGINE_NAME = "Aequor Measurement Quality Engine"
THRESHOLD_REVISION = "quality-v1"

@dataclass(frozen=True)
class QualityThresholdConfig:
    # Prototype engineering thresholds; units are explicit and not clinical.
    motion_acceleration_sd_m_s2: float = 0.08
    motion_acceleration_range_m_s2: float = 0.35
    motion_gyro_rms_rad_s: float = 0.08
    motion_gyro_sd_rad_s: float = 0.06
    motion_gyro_max_rad_s: float = 0.18
    posture_drift_deg: float = 5.0
    contact_median_max_ohm: float = 3000.0
    contact_cv: float = 0.08
    contact_range_ohm: float = 250.0
    temperature_sd_c: float = 0.12
    temperature_range_c: float = 0.4
    temperature_drift_c: float = 0.3
    minimum_samples: int = 2
    overall_threshold: float = 70.0
    critical_minimum: float = 45.0
    weight_motion: float = 0.30
    weight_posture: float = 0.20
    weight_contact: float = 0.25
    weight_temperature: float = 0.10
    weight_integrity: float = 0.15

    @property
    def weights(self) -> dict[str, float]:
        return {"motion": self.weight_motion, "posture": self.weight_posture, "contact": self.weight_contact, "temperature": self.weight_temperature, "integrity": self.weight_integrity}

DEFAULT_THRESHOLDS = QualityThresholdConfig()

def public_thresholds(config: QualityThresholdConfig = DEFAULT_THRESHOLDS) -> dict[str, object]:
    return {"quality_engine_name": QUALITY_ENGINE_NAME, "threshold_revision": THRESHOLD_REVISION, "label": "PROTOTYPE ENGINEERING THRESHOLDS — not clinically validated", "weights": config.weights, "thresholds": {k: v for k, v in config.__dict__.items() if k.startswith(("motion_", "posture_", "contact_", "temperature_", "minimum_", "overall_", "critical_"))}}
