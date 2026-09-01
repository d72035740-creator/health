from typing import Annotated
from pydantic import AwareDatetime, Field
from app.domain.enums import DataProvenance
from app.domain.models import ContractModel

Finite = float

class FrequencyFeature(ContractModel):
    frequency_hz: Annotated[float, Field(gt=0)]
    magnitude_ratio: float
    log_magnitude_ratio: float
    abs_log_magnitude_ratio: float
    resistance_ratio: float
    reactance_difference_ohm: float
    phase_difference_deg: float
    abs_phase_difference_deg: float
    normalized_magnitude_difference: float

class SpectralFeatures(ContractModel):
    low_high_magnitude_ratio: float
    low_high_resistance_ratio: float
    magnitude_log_frequency_slope_ohm_per_log10_hz: float
    resistance_log_frequency_slope_ohm_per_log10_hz: float
    phase_range_deg: float
    reactance_peak_ohm: float | None = None

class ColeFitResult(ContractModel):
    fit_success: bool
    r0_ohm: float | None = None
    rinf_ohm: float | None = None
    tau_seconds: float | None = None
    beta: float | None = None
    complex_rmse_ohm: float | None = None
    failure_reason: str | None = None

class BilateralColeFeatures(ContractModel):
    fitted_r0_ratio: float | None = None
    fitted_rinf_ratio: float | None = None
    fitted_tau_ratio: float | None = None
    fitted_beta_difference: float | None = None

class QualityContext(ContractModel):
    technical_quality_score: float
    left_mean_skin_temperature_c: float | None = None
    right_mean_skin_temperature_c: float | None = None

class ProcessedBioimpedanceFeatures(ContractModel):
    measurement_attempt_id: str
    sweep_pair_id: str
    simulated_time: AwareDatetime
    provenance: DataProvenance
    processor_name: str
    feature_revision: str
    per_frequency_features: list[FrequencyFeature]
    left_spectral_features: SpectralFeatures
    right_spectral_features: SpectralFeatures
    left_cole_fit: ColeFitResult
    right_cole_fit: ColeFitResult
    bilateral_cole_features: BilateralColeFeatures
    quality_context: QualityContext

    def to_ml_vector(self) -> dict[str, object]:
        values: list[float] = []; names: list[str] = []
        for point in self.per_frequency_features:
            for name in ("magnitude_ratio", "log_magnitude_ratio", "phase_difference_deg", "normalized_magnitude_difference"):
                names.append(f"{name}_{int(point.frequency_hz)}hz"); values.append(float(getattr(point, name)))
        for side, spectral in (("left", self.left_spectral_features), ("right", self.right_spectral_features)):
            for name in ("low_high_magnitude_ratio", "low_high_resistance_ratio", "magnitude_log_frequency_slope_ohm_per_log10_hz", "resistance_log_frequency_slope_ohm_per_log10_hz", "phase_range_deg"):
                names.append(f"{side}_{name}"); values.append(float(getattr(spectral, name)))
        return {"feature_revision": self.feature_revision, "names": names, "values": values}
