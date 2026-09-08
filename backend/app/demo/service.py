from threading import RLock

from app.baseline.service import baseline_service
from app.demo.models import CompetitionDemoSnapshot,DemoTrendPoint
from app.domain.enums import ArmSide
from app.measurement import measurement_attempt_service
from app.runtime import runtime_service
from app.scenario import ScenarioType,scenario_provider
from app.simulation.engine import simulation_engine
from app.simulation.sensors.models import SensorWindowRequest
from app.timeline.models import TimelineEventSource,TimelineEventType
from app.timeline.service import timeline_service
from app.views.service import clinician_view_service,patient_view_service


STEPS=['Establish Personalized Baseline','Verify Normal Stable Pattern','Introduce Slow Unilateral Change','Observe Edge-AI + Temporal Evidence','View Patient Experience','View Clinician Evidence','Challenge Aequor']
class DemoError(RuntimeError):pass
class CompetitionDemoService:
 def __init__(self):self._lock=RLock();self._step=1;self._busy=False;self._checkpoint_index=0;self._total_checkpoints=3;self._active_experiment=None;simulation_engine.register_reset_hook(self._on_reset)
 def _on_reset(self):self._step=1;self._busy=False;self._checkpoint_index=0;self._active_experiment=None
 def reset(self):simulation_engine.reset();return self.snapshot()
 def establish_baseline(self):
  with self._lock:
   if self._busy:raise DemoError('Demo action already running')
   self._busy=True
   try:
    simulation_engine.reset();baseline_service.start();timeline_service.append(TimelineEventType.BASELINE_CALIBRATION_STARTED,TimelineEventSource.RUNTIME,'Baseline calibration started','Guided competition demo calibration began.')
    for index in range(28):
     attempt=measurement_attempt_service.attempt(SensorWindowRequest());baseline_service.capture(attempt.processed_features)
     if index<27:simulation_engine.step(6*3600 if index<24 else 12*3600)
    baseline_service.finalize();base=baseline_service.snapshot();timeline_service.append(TimelineEventType.BASELINE_ESTABLISHED,TimelineEventSource.RUNTIME,'Baseline established',f'Personal reference established from {base.observation_count} qualified observations.');self._step=2
   finally:self._busy=False
  return self.snapshot()
 def verify_stable(self):
  with self._lock:
   if baseline_service.snapshot().state.value!='READY':raise DemoError('Establish the personalized baseline first')
   cycle=runtime_service.measure(SensorWindowRequest());self._step=3
  return self.snapshot()
 def start_slow_left(self):
  with self._lock:
   if self._busy:raise DemoError('Demo action already running')
   if baseline_service.snapshot().state.value!='READY':raise DemoError('Establish the personalized baseline first')
   self._busy=True
   try:
    scenario_provider.select(ScenarioType.SLOW_UNILATERAL_SHIFT,ArmSide.LEFT);selected=scenario_provider.state().as_dict();timeline_service.append(TimelineEventType.SCENARIO_SELECTED,TimelineEventSource.SCENARIO_ENGINE,'Scenario selected','Guided demo selected SLOW_UNILATERAL_SHIFT.',scenario_ground_truth=selected)
    scenario_provider.start();started=scenario_provider.state().as_dict();timeline_service.append(TimelineEventType.SCENARIO_STARTED,TimelineEventSource.SCENARIO_ENGINE,'Scenario started','Guided demo started slow LEFT synthetic physiology.',scenario_ground_truth=started)
    self._checkpoint_index=0;self._active_experiment='SLOW_UNILATERAL_LEFT';self._step=3
   finally:self._busy=False
  return self.snapshot()
 def next_checkpoint(self):
  with self._lock:
   if self._busy:raise DemoError('Demo action already running')
   if baseline_service.snapshot().state.value!='READY':raise DemoError('Establish the personalized baseline first')
   if not scenario_provider.state().active:self.start_slow_left()
   self._busy=True
   try:
    snap=simulation_engine.step(2*86400);timeline_service.append(TimelineEventType.SIMULATION_TIME_ADVANCED,TimelineEventSource.SIMULATION_CONTROL,'Simulation time advanced','Guided demo advanced two simulated days.',simulated_time=snap.simulated_time);runtime_service.measure(SensorWindowRequest())
    self._checkpoint_index+=1
    if self._checkpoint_index>=self._total_checkpoints:self._step=4
    else:self._step=3
   finally:self._busy=False
  return self.snapshot()
 def run_slow_left(self):
  with self._lock:
   if self._busy:raise DemoError('Demo action already running')
   if baseline_service.snapshot().state.value!='READY':raise DemoError('Establish the personalized baseline first')
   self._busy=True
   try:
    scenario_provider.select(ScenarioType.SLOW_UNILATERAL_SHIFT,ArmSide.LEFT);selected=scenario_provider.state().as_dict();timeline_service.append(TimelineEventType.SCENARIO_SELECTED,TimelineEventSource.SCENARIO_ENGINE,'Scenario selected','Guided demo selected SLOW_UNILATERAL_SHIFT.',scenario_ground_truth=selected)
    scenario_provider.start();started=scenario_provider.state().as_dict();timeline_service.append(TimelineEventType.SCENARIO_STARTED,TimelineEventSource.SCENARIO_ENGINE,'Scenario started','Guided demo started slow LEFT synthetic physiology.',scenario_ground_truth=started)
    self._active_experiment='SLOW_UNILATERAL_LEFT'
    for _ in range(3):
     snap=simulation_engine.step(2*86400);timeline_service.append(TimelineEventType.SIMULATION_TIME_ADVANCED,TimelineEventSource.SIMULATION_CONTROL,'Simulation time advanced','Guided demo advanced two simulated days.',simulated_time=snap.simulated_time);runtime_service.measure(SensorWindowRequest())
    self._checkpoint_index=3;self._step=4
   finally:self._busy=False
  return self.snapshot()
 @staticmethod
 def _relative(attempt):
  if not attempt.baseline_comparison:return None,None
  values={x.name:x.signed_normalized_delta for x in attempt.baseline_comparison.values};left=[v for k,v in values.items() if k.startswith('left_')];right=[v for k,v in values.items() if k.startswith('right_')]
  return 100+(sum(left)/len(left) if left else 0),100+(sum(right)/len(right) if right else 0)
 def snapshot(self):
  base=baseline_service.snapshot();state=scenario_provider.state();history=runtime_service.history();latest=runtime_service.snapshot();trend=[]
  for cycle in history:
   attempt=cycle.attempt
   if attempt.quality_assessment.qualification.value!='QUALIFIED':continue
   left,right=self._relative(attempt);temporal=attempt.temporal_assessment;decision=attempt.decision_snapshot
   trend.append(DemoTrendPoint(simulated_time=cycle.simulated_time,left_relative_pattern=left,right_relative_pattern=right,novelty_z=attempt.ml_inference.novelty_z if attempt.ml_inference else None,ewma=temporal.ewma_novelty if temporal else None,adi=decision.adi if decision else None,surveillance_state=cycle.current_surveillance_state))
  observed=None
  latest_pipeline=None
  if latest:
   a=latest.attempt;t=a.temporal_assessment;c=a.confounder_assessment;d=a.decision_snapshot
   stage_status={x:'NOT_RUN' for x in ('SENSORS','QUALITY','BIS','FEATURES','BASELINE','TINYML','TEMPORAL','CONFOUNDERS','DECISION')}
   for ev in latest.pipeline_events:stage_status[ev.stage]='BLOCKED' if ev.status=='REJECTED' else ev.status
   if latest.pipeline_status.value=='BLOCKED_BY_QUALITY':stage_status['QUALITY']='BLOCKED'
   latest_pipeline=[{'stage':k,'status':v} for k,v in stage_status.items()]
   dev_summary='Within normal personal variation' if not a.ml_inference else ('Elevated deviation from baseline' if (a.ml_inference.novelty_z or 0)>3.0 else ('Moderate deviation from baseline' if (a.ml_inference.novelty_z or 0)>2.0 else 'Within expected baseline bounds'))
   sys_val=c.systemic_bilateral_evidence if c else 0.0
   sys_lbl='HIGH' if sys_val>0.66 else ('MODERATE' if sys_val>0.33 else 'LOW')
   observed={'quality':a.quality_assessment.qualification.value,'quality_score':a.quality_assessment.overall_score,'rejection_reasons':[x.value for x in a.quality_assessment.rejection_reasons],'pipeline_status':latest.pipeline_status.value,'dominant_observed_side':d.dominant_observed_side if d else None,'novelty_z':a.ml_inference.novelty_z if a.ml_inference else None,'reconstruction_error':a.ml_inference.reconstruction_error_mse if a.ml_inference else None,'personal_deviation_summary':dev_summary,'ewma':t.ewma_novelty if t else None,'cusum':t.cusum_value if t else None,'persistence_days':t.persistence_duration_days if t else None,'systemic_evidence':sys_val,'systemic_label':sys_lbl,'unilateral_evidence':c.unilateral_asymmetry_score if c else None,'adi':d.adi if d else None,'surveillance_state':latest.current_surveillance_state,'decision_updated':latest.cycle_decision_updated,'cycle_index':latest.cycle_index,'simulated_time':str(latest.simulated_time)}

  try:
   patient_snap=patient_view_service.snapshot().model_dump(mode='json')
   clinician_snap=clinician_view_service.snapshot().model_dump(mode='json')
  except Exception:
   patient_snap=None;clinician_snap=None
  return CompetitionDemoSnapshot(title='AEQUOR COMPETITION DEMO',step_index=self._step,total_steps=7,step_title=STEPS[self._step-1],busy=self._busy,baseline={'state':base.state.value,'observations':base.observation_count,'span_days':base.simulated_span_seconds/86400},scenario_ground_truth=state.as_dict(),observed=observed,trend=trend,runtime_cycle_ids=[x.cycle_id for x in history],disclosure='SIMULATED SENSING • REAL EXECUTABLE AI PIPELINE',automation_boundary='Demo automation sets scenario, simulated time, sensor condition, and measurement timing only. It never sets novelty, ADI, observed side, or surveillance state.',checkpoint_index=self._checkpoint_index,total_checkpoints=self._total_checkpoints,active_experiment=self._active_experiment,latest_pipeline=latest_pipeline,patient_preview=patient_snap,clinician_preview=clinician_snap)


demo_service=CompetitionDemoService()
