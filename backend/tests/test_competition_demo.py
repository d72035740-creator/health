from fastapi.testclient import TestClient
from app.main import app
from app.runtime import runtime_service
from app.simulation.engine import simulation_engine


client=TestClient(app)
def setup_function():simulation_engine.reset()


def test_demo_requires_legal_order_and_clean_reset():
 assert client.post('/api/v1/demo/stable').status_code==409
 body=client.post('/api/v1/demo/reset').json()
 assert body['step_index']==1 and body['baseline']['state']=='UNINITIALIZED'
 assert body['runtime_cycle_ids']==[]


def test_demo_baseline_and_stable_use_real_pipeline():
 base=client.post('/api/v1/demo/baseline').json();assert base['baseline']['state']=='READY';assert base['baseline']['observations']==28;assert base['step_index']==2
 stable=client.post('/api/v1/demo/stable').json();cycle=runtime_service.snapshot()
 assert stable['step_index']==3;assert stable['observed']['quality']=='QUALIFIED';assert stable['observed']['adi']==cycle.attempt.decision_snapshot.adi;assert stable['observed']['surveillance_state']==cycle.current_surveillance_state


def test_slow_left_demo_outputs_emerge_from_runtime_and_timeline():
 client.post('/api/v1/demo/baseline');client.post('/api/v1/demo/stable');body=client.post('/api/v1/demo/slow-left').json();latest=runtime_service.snapshot()
 assert body['step_index']==4;assert body['scenario_ground_truth']['affected_arm']=='LEFT';assert len(body['trend'])==4
 assert body['observed']['dominant_observed_side']==latest.attempt.decision_snapshot.dominant_observed_side
 assert body['observed']['novelty_z']==latest.attempt.ml_inference.novelty_z
 assert body['observed']['adi']==latest.attempt.decision_snapshot.adi
 assert body['observed']['surveillance_state']==latest.current_surveillance_state
 timeline=client.get('/api/v1/views/timeline').json();types={x['event_type'] for x in timeline['events']}
 assert {'SCENARIO_SELECTED','SCENARIO_STARTED','SIMULATION_TIME_ADVANCED','MEASUREMENT_QUALIFIED'}.issubset(types)


def test_demo_reset_restores_usable_clean_state():
 client.post('/api/v1/demo/baseline');client.post('/api/v1/demo/stable');body=client.post('/api/v1/demo/reset').json()
 assert body['baseline']['state']=='UNINITIALIZED';assert body['observed'] is None;assert runtime_service.snapshot() is None


def test_step_by_step_checkpoints_and_anti_leakage():
 client.post('/api/v1/demo/baseline')
 started=client.post('/api/v1/demo/start-slow-left').json()
 assert started['checkpoint_index']==0;assert started['total_checkpoints']==3
 assert started['scenario_ground_truth']['affected_arm']=='LEFT'
 c1=client.post('/api/v1/demo/checkpoint').json()
 assert c1['checkpoint_index']==1;assert c1['step_index']==3
 assert c1['observed']['quality']=='QUALIFIED'
 c2=client.post('/api/v1/demo/checkpoint').json()
 assert c2['checkpoint_index']==2
 c3=client.post('/api/v1/demo/checkpoint').json()
 assert c3['checkpoint_index']==3;assert c3['step_index']==4
 # Verify pipeline events are populated
 stages=[x['stage'] for x in c3['latest_pipeline']]
 assert 'SENSORS' in stages and 'QUALITY' in stages and 'DECISION' in stages
 # Anti-leakage: scenario truth forbidden in observed, patient_preview, clinician_preview
 forbidden={'scenario_type','scenario_id','affected_arm'}
 def check_keys(d):
  if isinstance(d,dict):
   for k,v in d.items():
    assert k not in forbidden, f"Leakage detected: {k}"
    check_keys(v)
  elif isinstance(d,list):
   for item in d:check_keys(item)
 check_keys(c3['observed'])
 if c3['patient_preview']:check_keys(c3['patient_preview'])
 if c3['clinician_preview']:check_keys(c3['clinician_preview'])
