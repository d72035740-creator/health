import math
import pytest
from app.signal_processing.config import EXPECTED_FREQUENCIES_HZ
from app.signal_processing.processor import feature_processor, SignalProcessingError
from app.signal_processing.spectral import _slope
from app.signal_processing.validation import ProcessingValidationError, validate_sweep
from app.simulation.engine import DigitalPatientEngine
from app.simulation.sensors.models import SensorWindowRequest, MotionCondition
from app.measurement import MeasurementAttemptService

def qualified_attempt():
    engine=DigitalPatientEngine(); engine.create(); return MeasurementAttemptService().attempt(SensorWindowRequest())

def test_qualified_attempt_contains_named_processed_features():
    attempt=qualified_attempt(); assert attempt.processed_features is not None; features=attempt.processed_features
    assert features.sweep_pair_id==attempt.bis_sweep.pair_id; assert len(features.per_frequency_features)==6
    assert features.feature_revision=="bis-features-v1"; assert len(features.to_ml_vector()["values"])>0

def test_frequency_formulas_and_spectral_slope():
    f=qualified_attempt().processed_features; assert f is not None; point=f.per_frequency_features[0]
    assert point.magnitude_ratio == pytest.approx(math.exp(point.log_magnitude_ratio)); assert point.normalized_magnitude_difference == pytest.approx((point.magnitude_ratio-1)/((point.magnitude_ratio+1)/2))
    assert f.left_spectral_features.low_high_magnitude_ratio > 0
    assert _slope([1,2,3],[2,4,6])==pytest.approx(2)

def test_validation_rejects_mismatched_and_inconsistent_sweeps():
    attempt=qualified_attempt(); sweep=attempt.bis_sweep; assert sweep is not None
    broken=sweep.model_copy(deep=True); broken.right.points=broken.right.points[:-1]
    with pytest.raises(ProcessingValidationError): validate_sweep(broken,EXPECTED_FREQUENCIES_HZ)
    broken=sweep.model_copy(deep=True); broken.left.points[0].magnitude_ohm=1
    with pytest.raises(ProcessingValidationError): validate_sweep(broken,EXPECTED_FREQUENCIES_HZ)

def test_rejected_attempt_has_no_processed_features():
    engine=DigitalPatientEngine(); engine.create(); service=MeasurementAttemptService(); attempt=service.attempt(SensorWindowRequest(motion_condition=MotionCondition.ACTIVE_MOTION)); assert attempt.bis_sweep is None and attempt.processed_features is None

def test_processor_refuses_unqualified_input():
    attempt=qualified_attempt(); attempt.quality_assessment.qualification="REJECTED"
    with pytest.raises(SignalProcessingError): feature_processor.process_attempt(attempt)
