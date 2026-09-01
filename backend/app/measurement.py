from threading import RLock
from app.quality.engine import MeasurementQualityEngine, quality_engine
from app.quality.models import MeasurementAttempt, MeasurementQualification
from app.simulation.bioimpedance.service import BilateralBioimpedanceService, bioimpedance_service
from app.simulation.sensors.models import SensorWindowRequest
from app.simulation.sensors.service import WearableSensorService, wearable_sensor_service
from app.signal_processing.processor import BISFeatureProcessor, feature_processor
from app.baseline.service import baseline_service
from app.ml.runtime import ml_runtime
from app.temporal.service import temporal_service
from app.confounders.service import confounder_service
from app.decision.service import decision_service

class MeasurementAttemptService:
    def __init__(self, *, sensors: WearableSensorService = wearable_sensor_service, quality: MeasurementQualityEngine = quality_engine, bis: BilateralBioimpedanceService = bioimpedance_service, processor: BISFeatureProcessor = feature_processor) -> None:
        self._lock=RLock(); self._sensors=sensors; self._quality=quality; self._bis=bis; self._processor=processor; self._attempt_index=0
        sensors._engine.register_reset_hook(self.reset)
    def reset(self) -> None:
        with self._lock: self._attempt_index=0
    def attempt(self, request: SensorWindowRequest) -> MeasurementAttempt:
        with self._lock:
            window=self._sensors.acquire(request); assessment=self._quality.evaluate(window); self._attempt_index += 1; index=self._attempt_index
            sweep=self._bis.acquire() if assessment.qualification is MeasurementQualification.QUALIFIED else None
            attempt=MeasurementAttempt.model_construct(attempt_id=f"{window.simulation_id}:attempt:{index}", attempt_index=index, simulated_time=window.anchor_simulated_time, sensor_window=window, quality_assessment=assessment, bis_sweep=sweep, processed_features=None, baseline_comparison=None, ml_inference=None, temporal_assessment=None, confounder_assessment=None, decision_snapshot=None)
            if sweep is not None:
                attempt.processed_features=self._processor.process_attempt(attempt)
                if baseline_service.snapshot().state.value == "READY": attempt.baseline_comparison=baseline_service.compare(attempt.processed_features)
                if attempt.baseline_comparison is not None and ml_runtime._interpreter is not None:
                    attempt.ml_inference=ml_runtime.infer([v.signed_normalized_delta for v in attempt.baseline_comparison.values])
                    if attempt.ml_inference.status == 'READY':
                        attempt.temporal_assessment=temporal_service.observe(attempt_id=attempt.attempt_id, simulated_time=attempt.simulated_time, ml=attempt.ml_inference)
                        attempt.confounder_assessment=confounder_service.assess(attempt, attempt.temporal_assessment)
                        attempt.decision_snapshot=decision_service.evaluate(attempt)
            return MeasurementAttempt.model_validate(attempt)

measurement_attempt_service=MeasurementAttemptService()
