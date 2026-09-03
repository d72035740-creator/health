from app.runtime import runtime_service, RuntimePipelineStatus
from app.simulation.engine import simulation_engine
from app.simulation.sensors.models import SensorWindowRequest, MotionCondition
from app.baseline.service import baseline_service
from app.measurement import measurement_attempt_service
from fastapi.testclient import TestClient
from app.main import app

def setup_function(): simulation_engine.reset(); runtime_service.reset()
def test_rejection_blocks_downstream_and_no_baseline_waits():
 blocked=runtime_service.measure(SensorWindowRequest(motion_condition=MotionCondition.ACTIVE_MOTION)); assert blocked.pipeline_status is RuntimePipelineStatus.BLOCKED_BY_QUALITY; assert blocked.attempt.bis_sweep is None and not blocked.cycle_decision_updated
 waiting=runtime_service.measure(SensorWindowRequest()); assert waiting.pipeline_status is RuntimePipelineStatus.WAITING_FOR_BASELINE; assert waiting.attempt.ml_inference is None
def test_runtime_history_and_reset_are_deterministic():
 one=runtime_service.measure(SensorWindowRequest()); assert one.cycle_index==1 and len(runtime_service.history())==1; runtime_service.reset(); two=runtime_service.measure(SensorWindowRequest()); assert two.cycle_index==1
def test_runtime_websocket_connects_and_emits_snapshot():
 with TestClient(app).websocket_connect('/ws/runtime') as ws:
  message=ws.receive_json(); assert message['type']=='runtime.snapshot' and 'status' in message
