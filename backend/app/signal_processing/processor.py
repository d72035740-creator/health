from app.quality.models import MeasurementQualification
from app.signal_processing.cole_fit import fit_cole
from app.signal_processing.config import EXPECTED_FREQUENCIES_HZ, FEATURE_REVISION, PROCESSOR_NAME
from app.signal_processing.models import BilateralColeFeatures, ProcessedBioimpedanceFeatures, QualityContext
from app.signal_processing.spectral import arm_spectral, bilateral_features
from app.signal_processing.validation import validate_sweep

class SignalProcessingError(ValueError): pass

class BISFeatureProcessor:
    def process_attempt(self, attempt: object) -> ProcessedBioimpedanceFeatures:
        if getattr(attempt.quality_assessment,"qualification",None) is not MeasurementQualification.QUALIFIED or getattr(attempt,"bis_sweep",None) is None: raise SignalProcessingError("only qualified attempts with BIS may be processed")
        sweep=attempt.bis_sweep; validate_sweep(sweep,EXPECTED_FREQUENCIES_HZ)
        left_fit=fit_cole(sweep.left); right_fit=fit_cole(sweep.right); bilateral=BilateralColeFeatures()
        if left_fit.fit_success and right_fit.fit_success:
            bilateral=BilateralColeFeatures(fitted_r0_ratio=left_fit.r0_ohm/right_fit.r0_ohm,fitted_rinf_ratio=left_fit.rinf_ohm/right_fit.rinf_ohm,fitted_tau_ratio=left_fit.tau_seconds/right_fit.tau_seconds,fitted_beta_difference=left_fit.beta-right_fit.beta)
        context=attempt.quality_assessment
        temps=context.feature_summary
        return ProcessedBioimpedanceFeatures(measurement_attempt_id=attempt.attempt_id,sweep_pair_id=sweep.pair_id,simulated_time=sweep.simulated_time,provenance=sweep.provenance,processor_name=PROCESSOR_NAME,feature_revision=FEATURE_REVISION,per_frequency_features=bilateral_features(sweep.left,sweep.right),left_spectral_features=arm_spectral(sweep.left),right_spectral_features=arm_spectral(sweep.right),left_cole_fit=left_fit,right_cole_fit=right_fit,bilateral_cole_features=bilateral,quality_context=QualityContext(technical_quality_score=attempt.quality_assessment.overall_score,left_mean_skin_temperature_c=temps.get("LEFT").temperature_mean_c if temps.get("LEFT") else None,right_mean_skin_temperature_c=temps.get("RIGHT").temperature_mean_c if temps.get("RIGHT") else None))

feature_processor=BISFeatureProcessor()
