from fastapi.testclient import TestClient
from app.main import app
from app.runtime import runtime_service
from app.simulation.engine import simulation_engine
from app.simulation.sensors.models import SensorWindowRequest,MotionCondition
from app.views.service import patient_view_service,clinician_view_service

client=TestClient(app)
def keys(v):
 if isinstance(v,dict):return set(v)|{x for child in v.values() for x in keys(child)}
 if isinstance(v,list):return {x for child in v for x in keys(child)}
 return set()
def setup_function():simulation_engine.reset();runtime_service.reset()
def test_engineering_view_provenance_config_and_model_metadata():
 body=client.get('/api/v1/views/engineering').json();assert body['tinyml']['model_size_bytes']==9008;assert body['adi_configuration']['weights']['temporal']==.35;assert 'physiology' in body['provenance']['simulated_inputs'];assert 'INT8 TFLite inference' in body['provenance']['executable_software'];assert 'disease_probability' not in keys(body)
def test_rejected_pipeline_marks_downstream_not_run_and_no_stale_cycle_decision():
 runtime_service.measure(SensorWindowRequest(motion_condition=MotionCondition.ACTIVE_MOTION));body=client.get('/api/v1/views/engineering').json();stages={x['stage']:x['status'] for x in body['pipeline']};assert stages['QUALITY']=='BLOCKED';assert stages['BIS']=='NOT_RUN';assert body['latest_cycle']['decision_updated'] is False;assert body['tinyml']['latest'] is None
def test_lab_contains_truth_while_product_views_remain_blind():
 lab=client.get('/api/v1/views/lab').json();assert 'scenario_type' in lab['scenario_ground_truth']
 for view in (patient_view_service.snapshot().model_dump(),clinician_view_service.snapshot().model_dump()): assert not {'scenario_type','scenario_id','severity','affected_arm'}&keys(view)
def test_active_motion_lab_cycle_has_no_downstream_results():
 snap=runtime_service.measure(SensorWindowRequest(motion_condition=MotionCondition.ACTIVE_MOTION));assert snap.pipeline_status.value=='BLOCKED_BY_QUALITY';assert snap.attempt.bis_sweep is snap.attempt.ml_inference is snap.attempt.temporal_assessment is snap.attempt.decision_snapshot is None
