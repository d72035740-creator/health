from fastapi.testclient import TestClient
from app.main import app
from app.views.service import COPY
from app.simulation.engine import simulation_engine
from app.runtime import runtime_service
from app.simulation.sensors.models import SensorWindowRequest,MotionCondition

client=TestClient(app)
FORBIDDEN={'scenario_type','scenario_id','severity','affected_arm','r_zero_ohm','r_infinity_ohm','tau_seconds','beta','tflite','novelty_z','cusum_value','reconstruction_error_mse','diagnosis','disease_probability','risk_percentage'}
def keys(value):
 if isinstance(value,dict): return set(value)|{k for v in value.values() for k in keys(v)}
 if isinstance(value,list): return {k for v in value for k in keys(v)}
 return set()
def setup_function(): simulation_engine.reset();runtime_service.reset()
def test_patient_view_empty_and_information_boundary():
 body=client.get('/api/v1/views/patient').json(); assert body['surveillance_state']=='CALIBRATING'; assert body['latest_measurement'] is None; assert FORBIDDEN.isdisjoint(keys(body))
def test_patient_copy_is_conservative_and_deterministic():
 assert set(COPY)=={'CALIBRATING','WITHIN_PERSONAL_BASELINE','OBSERVING_CHANGE','PERSISTENT_DEVIATION','CLINICAL_REVIEW_RECOMMENDED'}; assert 'not a diagnosis' in COPY['CLINICAL_REVIEW_RECOMMENDED'][1].lower(); assert all('lymphedema' not in ' '.join(v).lower() for v in COPY.values())
def test_patient_rejected_attempt_is_skipped_and_does_not_update_state():
 runtime_service.measure(SensorWindowRequest(motion_condition=MotionCondition.ACTIVE_MOTION)); body=client.get('/api/v1/views/patient').json(); assert 'Not used' in body['latest_measurement']['technical_quality_label']; assert body['latest_measurement']['updated_surveillance_state'] is False
def test_clinician_view_is_more_detailed_but_scenario_blind():
 patient=client.get('/api/v1/views/patient').json(); clinician=client.get('/api/v1/views/clinician').json(); assert FORBIDDEN.isdisjoint(keys(clinician)); assert 'decision_components' in clinician and 'decision_components' not in patient; assert clinician['adi_label']=='Prototype research index — not disease probability'
