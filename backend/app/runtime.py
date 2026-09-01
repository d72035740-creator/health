from threading import RLock
from app.measurement import measurement_attempt_service
from app.simulation.sensors.models import SensorWindowRequest
class AequorRuntime:
 def __init__(self): self._lock=RLock(); self._latest=None; self._history=[]
 def measure(self,request:SensorWindowRequest):
  with self._lock:
   a=measurement_attempt_service.attempt(request); self._latest=a; self._history.append(a); return a
 def reset(self):
  with self._lock: self._latest=None; self._history=[]
 def status(self): return {'runtime_name':'Aequor Integrated Runtime','runtime_revision':'runtime-v1','ready':True,'latest_cycle':self._latest.attempt_id if self._latest else None,'latest_pipeline_status':'COMPLETED' if self._latest and self._latest.ml_inference else 'WAITING_FOR_BASELINE' if self._latest else None,'current_surveillance_state':self._latest.decision_snapshot.surveillance_state.value if self._latest and self._latest.decision_snapshot else 'CALIBRATING'}
runtime_service=AequorRuntime()
