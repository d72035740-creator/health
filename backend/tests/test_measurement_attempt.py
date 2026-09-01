from app.measurement import MeasurementAttemptService
from app.quality.models import MeasurementQualification
from app.simulation.engine import DigitalPatientEngine
from app.simulation.sensors.models import MotionCondition, SensorWindowRequest
from app.simulation.sensors.service import WearableSensorService
from app.simulation.bioimpedance.service import BilateralBioimpedanceService

def test_rejected_attempt_does_not_consume_bis_index():
    engine=DigitalPatientEngine(); engine.create(); sensors=WearableSensorService(engine=engine); bis=BilateralBioimpedanceService(engine=engine); service=MeasurementAttemptService(sensors=sensors,bis=bis)
    rejected=service.attempt(SensorWindowRequest(motion_condition=MotionCondition.ACTIVE_MOTION)); qualified=service.attempt(SensorWindowRequest())
    assert rejected.quality_assessment.qualification is MeasurementQualification.REJECTED and rejected.bis_sweep is None
    assert qualified.quality_assessment.qualification is MeasurementQualification.QUALIFIED and qualified.bis_sweep is not None
    assert qualified.bis_sweep.sweep_index == 1
