from enum import Enum
from threading import Lock, RLock
from app.domain.models import ContractModel
from app.measurement import measurement_attempt_service
from app.quality.models import MeasurementAttempt, MeasurementQualification
from app.simulation.sensors.models import SensorWindowRequest
from app.decision.service import decision_service

class RuntimePipelineStatus(str, Enum):
    COMPLETED='COMPLETED'; BLOCKED_BY_QUALITY='BLOCKED_BY_QUALITY'; WAITING_FOR_BASELINE='WAITING_FOR_BASELINE'; ML_UNAVAILABLE='ML_UNAVAILABLE'; PROCESSING_ERROR='PROCESSING_ERROR'
class RuntimePipelineEvent(ContractModel): stage:str; status:str; detail:str|None=None
class AequorRuntimeSnapshot(ContractModel):
    runtime_name:str='Aequor Integrated Runtime'; runtime_revision:str='runtime-v1'; cycle_id:str; cycle_index:int; simulated_time:object
    pipeline_status:RuntimePipelineStatus; pipeline_events:list[RuntimePipelineEvent]; attempt:MeasurementAttempt; cycle_decision_updated:bool; current_surveillance_state:str; last_decision_time:object|None
class RuntimeBusyError(RuntimeError): pass
class AequorRuntime:
    def __init__(self): self._gate=Lock(); self._lock=RLock(); self._latest=None; self._history=[]; self._index=0
    def measure(self,request:SensorWindowRequest):
        if not self._gate.acquire(blocking=False): raise RuntimeBusyError('measurement cycle already running')
        try:
            with self._lock: self._index+=1; index=self._index
            attempt=measurement_attempt_service.attempt(request); events=[RuntimePipelineEvent(stage='SENSORS',status='COMPLETED'),RuntimePipelineEvent(stage='QUALITY',status=attempt.quality_assessment.qualification.value)]
            if attempt.quality_assessment.qualification is MeasurementQualification.REJECTED: status=RuntimePipelineStatus.BLOCKED_BY_QUALITY
            elif attempt.baseline_comparison is None: status=RuntimePipelineStatus.WAITING_FOR_BASELINE; events += [RuntimePipelineEvent(stage='BIS',status='COMPLETED'),RuntimePipelineEvent(stage='FEATURES',status='COMPLETED'),RuntimePipelineEvent(stage='BASELINE',status='WAITING')]
            elif attempt.ml_inference is None: status=RuntimePipelineStatus.ML_UNAVAILABLE; events += [RuntimePipelineEvent(stage='BIS',status='COMPLETED'),RuntimePipelineEvent(stage='FEATURES',status='COMPLETED'),RuntimePipelineEvent(stage='BASELINE',status='COMPLETED'),RuntimePipelineEvent(stage='TINYML',status='UNAVAILABLE')]
            else: status=RuntimePipelineStatus.COMPLETED; events += [RuntimePipelineEvent(stage=x,status='COMPLETED') for x in ('BIS','FEATURES','BASELINE','TINYML','TEMPORAL','CONFOUNDERS','DECISION')]
            latest=decision_service.latest(); snap=AequorRuntimeSnapshot(cycle_id=attempt.attempt_id,cycle_index=index,simulated_time=attempt.simulated_time,pipeline_status=status,pipeline_events=events,attempt=attempt,cycle_decision_updated=attempt.decision_snapshot is not None,current_surveillance_state=latest.surveillance_state.value if latest else 'CALIBRATING',last_decision_time=latest.simulated_time if latest else None)
            with self._lock: self._latest=snap; self._history.append(snap)
            from app.scenario import scenario_provider
            from app.timeline.service import timeline_service
            timeline_service.record_runtime_cycle(snap, scenario_provider.state().as_dict())
            return snap
        finally: self._gate.release()
    def reset(self):
        with self._lock: self._latest=None; self._history=[]; self._index=0
    def snapshot(self): return self._latest
    def history(self): return list(self._history)
    def status(self):
        latest=decision_service.latest(); return {'runtime_name':'Aequor Integrated Runtime','runtime_revision':'runtime-v1','ready':True,'latest_cycle':self._latest.cycle_id if self._latest else None,'latest_pipeline_status':self._latest.pipeline_status.value if self._latest else None,'current_surveillance_state':latest.surveillance_state.value if latest else 'CALIBRATING'}
runtime_service=AequorRuntime()
from app.simulation.engine import simulation_engine
simulation_engine.register_reset_hook(runtime_service.reset)
