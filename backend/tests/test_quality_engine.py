import random
from app.quality.engine import quality_engine
from app.quality.models import MeasurementQualification, RejectionReason
from app.simulation.engine import DigitalPatientEngine
from app.simulation.sensors.models import ContactCondition, MotionCondition, SensorWindowRequest
from app.simulation.sensors.service import WearableSensorService

def build():
    engine=DigitalPatientEngine(); engine.create(); return engine, WearableSensorService(engine=engine)

def test_preset_quality_and_gating_signals():
    _, service=build()
    stable=quality_engine.evaluate(service.acquire(SensorWindowRequest()))
    active=quality_engine.evaluate(service.acquire(SensorWindowRequest(motion_condition=MotionCondition.ACTIVE_MOTION)))
    posture=quality_engine.evaluate(service.acquire(SensorWindowRequest(motion_condition=MotionCondition.POSTURE_TRANSITION)))
    poor=quality_engine.evaluate(service.acquire(SensorWindowRequest(contact_condition=ContactCondition.POOR_CONTACT)))
    assert stable.qualification is MeasurementQualification.QUALIFIED
    assert active.qualification is MeasurementQualification.REJECTED and RejectionReason.HIGH_MOTION in active.rejection_reasons
    assert posture.qualification is MeasurementQualification.REJECTED and RejectionReason.POSTURE_UNSTABLE in posture.rejection_reasons
    assert poor.qualification is MeasurementQualification.REJECTED and RejectionReason.CONTACT_IMPEDANCE_HIGH in poor.rejection_reasons
    assert all(0 <= value <= 100 for value in stable.dimension_scores.model_dump().values())

def test_temperature_offset_does_not_reduce_stability():
    _, service=build(); a=quality_engine.evaluate(service.acquire(SensorWindowRequest())); b=quality_engine.evaluate(service.acquire(SensorWindowRequest(temperature_offset_c=2)))
    assert b.dimension_scores.temperature_score >= a.dimension_scores.temperature_score - 5

def test_reset_and_global_random_are_independent():
    engine, service=build(); first=quality_engine.evaluate(service.acquire(SensorWindowRequest())); random.seed(123); [random.random() for _ in range(1000)]; engine.reset(); repeated=quality_engine.evaluate(service.acquire(SensorWindowRequest())); assert repeated.model_copy(update={"evaluated_at": first.evaluated_at}) == first
