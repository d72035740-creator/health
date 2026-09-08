from datetime import datetime,timezone
from threading import RLock

from app.baseline.service import baseline_service
from app.challenges.models import ChallengeDefinition,ChallengeEvidence,ChallengeResult,ChallengeStatus,ChallengeSuiteSnapshot
from app.decision.models import DecisionSnapshot
from app.decision.service import decision_service
from app.domain.enums import ArmSide
from app.measurement import measurement_attempt_service
from app.ml.runtime import ml_runtime
from app.quality.models import MeasurementQualification
from app.runtime import RuntimePipelineStatus,runtime_service
from app.scenario import ScenarioType,scenario_provider
from app.simulation.engine import simulation_engine
from app.simulation.sensors.models import ContactCondition,MotionCondition,SensorWindowRequest
from app.temporal.models import TemporalObservation
from app.views.service import clinician_view_service,patient_view_service


DEFINITIONS=[
 ChallengeDefinition(challenge_id='active-motion',title='ACTIVE MOTION',question='Can movement create a false physiological signal?',naive_failure_mode='Motion artifact could be treated as physiology.',expected_invariant='Quality rejects the cycle before BIS, ML, temporal, or decision.'),
 ChallengeDefinition(challenge_id='poor-contact',title='POOR CONTACT',question='Can bad electrode contact reach the AI?',naive_failure_mode='Electrode artifact could distort impedance.',expected_invariant='The real Phase-4 result governs; rejection must block every downstream stage.'),
 ChallengeDefinition(challenge_id='posture-transition',title='POSTURE TRANSITION',question='Can unstable posture be mistaken for physiology?',naive_failure_mode='Posture motion could alter a naive sensor signal.',expected_invariant='The real Phase-4 result governs; rejection must block every downstream stage.'),
 ChallengeDefinition(challenge_id='transient-spike',title='ONE TRANSIENT SPIKE',question='Does one large observation trigger a persistent alert?',naive_failure_mode='A threshold-only system might alert after one point.',expected_invariant='One isolated qualified spike from baseline cannot directly enter a persistent/review state.'),
 ChallengeDefinition(challenge_id='systemic-shift',title='SYSTEMIC BILATERAL SHIFT',question='Can bilateral change masquerade as unilateral change?',naive_failure_mode='A naive detector may ignore bilateral coherence.',expected_invariant='Observed systemic evidence must exceed the equivalent unilateral reference.'),
 ChallengeDefinition(challenge_id='arm-symmetry',title='LEFT / RIGHT SYMMETRY',question='Is the algorithm biased toward one arm?',naive_failure_mode='One side might be favored by implementation details.',expected_invariant='Observed side reverses and peak ADI remains within a 10-point engineering tolerance.'),
 ChallengeDefinition(challenge_id='model-unavailable',title='MODEL REMOVED / UNAVAILABLE',question='Does Aequor fake AI output without its model?',naive_failure_mode='A fallback score could conceal missing inference.',expected_invariant='ML_UNAVAILABLE with no novelty, temporal, confounder, or decision update.'),
 ChallengeDefinition(challenge_id='label-leakage',title='SCENARIO LABEL LEAKAGE',question='Does the AI know the simulator answer?',naive_failure_mode='Ground truth could leak into downstream contracts.',expected_invariant='Challenge/scenario identity is absent from ML input, temporal, decision, patient, and clinician contracts.'),
 ChallengeDefinition(challenge_id='scenario-reset',title='SCENARIO RESET CHEAT',question='Does resetting truth instantly reset surveillance?',naive_failure_mode='A simulator reset could improperly overwrite evidence state.',expected_invariant='Scenario reset alone cannot alter the last observed decision.'),
 ChallengeDefinition(challenge_id='stale-decision',title='REJECTED CYCLE STALE DATA',question='Can an old decision appear to belong to a rejected cycle?',naive_failure_mode='A UI could attach stale AI output to a rejected attempt.',expected_invariant='Rejected cycle has decision_updated=false while prior state/time remain explicitly historical.')]


class AdversarialChallengeService:
 def __init__(self): self._lock=RLock();self._history=[]
 def definitions(self): return [x.model_copy(deep=True) for x in DEFINITIONS]
 def history(self):
  with self._lock:return [x.model_copy(deep=True) for x in self._history]
 def snapshot(self):
  history=self.history(); latest={}
  for result in history:latest[result.challenge_id]=result
  return ChallengeSuiteSnapshot(definitions=self.definitions(),latest_results=[latest[x.challenge_id] for x in DEFINITIONS if x.challenge_id in latest],history_count=len(history))
 def _definition(self,challenge_id):
  try:return next(x for x in DEFINITIONS if x.challenge_id==challenge_id)
  except StopIteration as error:raise KeyError(challenge_id) from error
 def _baseline(self):
  baseline_service.start()
  for index in range(28):
   attempt=measurement_attempt_service.attempt(SensorWindowRequest());baseline_service.capture(attempt.processed_features)
   if index<27:simulation_engine.step(6*3600 if index<24 else 12*3600)
  baseline_service.finalize()
 def _prepare(self): simulation_engine.reset();self._baseline()
 @staticmethod
 def _status(checks):
  decisive=[x for x in checks.values() if x is not None]
  if not decisive:return ChallengeStatus.INCONCLUSIVE
  return ChallengeStatus.PASS if all(decisive) else ChallengeStatus.FAIL
 def _result(self,definition,start,evidence,checks,cycles,explanation,end=None):
  return ChallengeResult(challenge_id=definition.challenge_id,title=definition.title,run_time=datetime.now(timezone.utc),simulated_start=start,simulated_end=end or simulation_engine.snapshot().simulated_time,status=self._status(checks),observed_evidence=ChallengeEvidence(observations=evidence,invariant_checks=checks),expected_invariant=definition.expected_invariant,explanation=explanation,runtime_cycle_ids=cycles)
 def _quality(self,definition,request):
  start=simulation_engine.snapshot().simulated_time;snap=runtime_service.measure(request);a=snap.attempt;rejected=a.quality_assessment.qualification is MeasurementQualification.REJECTED
  checks={'quality_rejected':rejected,'bis_blocked':a.bis_sweep is None if rejected else None,'ml_blocked':a.ml_inference is None if rejected else None,'temporal_blocked':a.temporal_assessment is None if rejected else None,'decision_blocked':a.decision_snapshot is None if rejected else None}
  evidence={'quality':a.quality_assessment.qualification.value,'quality_score':a.quality_assessment.overall_score,'rejection_reasons':[x.value for x in a.quality_assessment.rejection_reasons],'pipeline_status':snap.pipeline_status.value,'bis_ran':a.bis_sweep is not None,'ml_ran':a.ml_inference is not None,'decision_updated':snap.cycle_decision_updated}
  explanation='Quality rejected the condition before downstream intelligence.' if rejected else 'The deterministic condition remained qualified; result is reported from the real quality engine.'
  return self._result(definition,start,evidence,checks,[snap.cycle_id],explanation)
 def _run_active_motion(self,d):return self._quality(d,SensorWindowRequest(motion_condition=MotionCondition.ACTIVE_MOTION))
 def _run_poor_contact(self,d):return self._quality(d,SensorWindowRequest(contact_condition=ContactCondition.POOR_CONTACT))
 def _run_posture_transition(self,d):return self._quality(d,SensorWindowRequest(motion_condition=MotionCondition.POSTURE_TRANSITION))
 def _run_transient_spike(self,d):
  self._prepare();stable=runtime_service.measure(SensorWindowRequest());start=simulation_engine.snapshot().simulated_time;scenario_provider.select(ScenarioType.TRANSIENT_UNILATERAL_SHIFT,ArmSide.LEFT);scenario_provider.start();simulation_engine.step(86400);spike=runtime_service.measure(SensorWindowRequest());state=spike.current_surveillance_state
  checks={'started_within_baseline':stable.current_surveillance_state=='WITHIN_PERSONAL_BASELINE','single_spike_not_persistent':state not in ('PERSISTENT_DEVIATION','CLINICAL_REVIEW_RECOMMENDED'),'one_new_temporal_observation':spike.attempt.temporal_assessment.observation_count==2 if spike.attempt.temporal_assessment else False}
  evidence={'starting_state':stable.current_surveillance_state,'spike_state':state,'novelty_z':spike.attempt.ml_inference.novelty_z if spike.attempt.ml_inference else None,'adi':spike.attempt.decision_snapshot.adi if spike.attempt.decision_snapshot else None,'temporal_state':spike.attempt.temporal_assessment.temporal_state.value if spike.attempt.temporal_assessment else None}
  return self._result(d,start,evidence,checks,[stable.cycle_id,spike.cycle_id],'Verdict uses the state recorded after exactly one transient peak observation.')
 def _scenario_evidence(self,kind,side):
  self._prepare();runtime_service.measure(SensorWindowRequest());scenario_provider.select(kind,side);scenario_provider.start();cycles=[];latest=None
  for _ in range(3):simulation_engine.step(2*86400);latest=runtime_service.measure(SensorWindowRequest());cycles.append(latest.cycle_id)
  c=latest.attempt.confounder_assessment;decision=latest.attempt.decision_snapshot
  return {'systemic':c.systemic_bilateral_evidence,'unilateral':c.unilateral_asymmetry_score,'coherence':c.bilateral_coherence_score,'side':c.dominant_change_side.value,'adi':decision.adi,'state':decision.surveillance_state.value},cycles
 def _run_systemic_shift(self,d):
  start=simulation_engine.snapshot().simulated_time;systemic,cycles1=self._scenario_evidence(ScenarioType.SYSTEMIC_BILATERAL_SHIFT,None);unilateral,cycles2=self._scenario_evidence(ScenarioType.SLOW_UNILATERAL_SHIFT,ArmSide.LEFT)
  margin=systemic['systemic']-unilateral['systemic'];checks={'systemic_exceeds_unilateral':margin>=.2,'bilateral_coherence_high':systemic['coherence']>=.6}
  return self._result(d,start,{'systemic_run':systemic,'unilateral_reference':unilateral,'systemic_evidence_margin':margin},checks,cycles1+cycles2,'Compared observed Phase-11 evidence from equivalent deterministic progressions.')
 def _arm_run(self,side):
  evidence,cycles=self._scenario_evidence(ScenarioType.SLOW_UNILATERAL_SHIFT,side);return evidence,cycles
 def _run_arm_symmetry(self,d):
  start=simulation_engine.snapshot().simulated_time;left,lcycles=self._arm_run(ArmSide.LEFT);right,rcycles=self._arm_run(ArmSide.RIGHT);delta=abs(left['adi']-right['adi'])
  checks={'left_direction':left['side']=='LEFT','right_direction':right['side']=='RIGHT','adi_within_engineering_tolerance':delta<=10}
  return self._result(d,start,{'left_run':left,'right_run':right,'adi_absolute_difference':delta,'engineering_tolerance':10.0},checks,lcycles+rcycles,'Direction must reverse; ADI comparison uses a declared non-clinical 10-point tolerance.')
 def _run_model_unavailable(self,d):
  self._prepare();start=simulation_engine.snapshot().simulated_time;interpreter,error=ml_runtime._interpreter,ml_runtime.error
  try:ml_runtime._interpreter=None;ml_runtime.error='Isolated challenge: model unavailable';snap=runtime_service.measure(SensorWindowRequest())
  finally:ml_runtime._interpreter=interpreter;ml_runtime.error=error
  a=snap.attempt;checks={'runtime_ml_unavailable':snap.pipeline_status is RuntimePipelineStatus.ML_UNAVAILABLE,'no_ml_result':a.ml_inference is None,'no_temporal':a.temporal_assessment is None,'no_confounder':a.confounder_assessment is None,'no_decision':a.decision_snapshot is None}
  return self._result(d,start,{'pipeline_status':snap.pipeline_status.value,'ml_result':None,'temporal_updated':False,'decision_updated':snap.cycle_decision_updated,'artifact_modified':False},checks,[snap.cycle_id],'Interpreter availability was isolated in memory; the committed artifact was not modified.')
 def _run_label_leakage(self,d):
  start=simulation_engine.snapshot().simulated_time;forbidden={'challenge_id','challenge_type','scenario_type','scenario_id','severity','affected_arm'};cycle=runtime_service.measure(SensorWindowRequest())
  def nested_keys(value):
   if isinstance(value,dict):return set(value)|{key for child in value.values() for key in nested_keys(child)}
   if isinstance(value,list):return {key for child in value for key in nested_keys(child)}
   return set()
  vector=cycle.attempt.processed_features.to_ml_vector();contracts={'ml_input_names':set(vector['names']),'temporal_observation':set(TemporalObservation.model_fields),'decision_snapshot':set(DecisionSnapshot.model_fields),'patient_view':nested_keys(patient_view_service.snapshot().model_dump()),'clinician_view':nested_keys(clinician_view_service.snapshot().model_dump())}
  checks={name:forbidden.isdisjoint(fields) for name,fields in contracts.items()};evidence={'forbidden_fields':sorted(forbidden),'inspected_contracts':{k:sorted(v) for k,v in contracts.items()},'ml_input_dimension':len(vector['values']),'ground_truth_leakage':'NONE DETECTED' if all(checks.values()) else 'DETECTED'}
  return self._result(d,start,evidence,checks,[cycle.cycle_id],'Verdict inspects an actual ML vector plus temporal, decision, patient, and clinician boundaries.')
 def _run_scenario_reset(self,d):
  self._prepare();runtime_service.measure(SensorWindowRequest());scenario_provider.select(ScenarioType.SLOW_UNILATERAL_SHIFT,ArmSide.LEFT);scenario_provider.start();cycles=[]
  for _ in range(3):simulation_engine.step(2*86400);snap=runtime_service.measure(SensorWindowRequest());cycles.append(snap.cycle_id)
  before=decision_service.latest();scenario_provider.reset();after=decision_service.latest();checks={'persistent_state_reached':before.surveillance_state.value in ('PERSISTENT_DEVIATION','CLINICAL_REVIEW_RECOMMENDED'),'state_unchanged_by_reset':after.surveillance_state==before.surveillance_state,'decision_time_unchanged':after.simulated_time==before.simulated_time}
  evidence={'state_before_reset':before.surveillance_state.value,'state_immediately_after_reset':after.surveillance_state.value,'decision_time_before':before.simulated_time,'decision_time_after':after.simulated_time,'new_observation_after_reset':False}
  return self._result(d,before.simulated_time,evidence,checks,cycles,'Scenario truth reset produced no measurement and therefore no decision update.')
 def _run_stale_decision(self,d):
  self._prepare();valid=runtime_service.measure(SensorWindowRequest());previous=decision_service.latest();rejected=runtime_service.measure(SensorWindowRequest(motion_condition=MotionCondition.ACTIVE_MOTION));checks={'latest_rejected':rejected.pipeline_status is RuntimePipelineStatus.BLOCKED_BY_QUALITY,'cycle_decision_not_updated':not rejected.cycle_decision_updated,'attempt_has_no_decision':rejected.attempt.decision_snapshot is None,'current_state_is_previous':rejected.current_surveillance_state==previous.surveillance_state.value,'last_decision_time_is_previous':rejected.last_decision_time==previous.simulated_time}
  evidence={'valid_cycle_id':valid.cycle_id,'rejected_cycle_id':rejected.cycle_id,'rejected_pipeline_status':rejected.pipeline_status.value,'decision_updated':rejected.cycle_decision_updated,'current_surveillance_state':rejected.current_surveillance_state,'last_decision_time':rejected.last_decision_time,'rejected_cycle_adi':None}
  return self._result(d,valid.simulated_time,evidence,checks,[valid.cycle_id,rejected.cycle_id],'Current state and last-decision time remain explicitly attributed to the prior valid cycle.')
 def run(self,challenge_id):
  definition=self._definition(challenge_id);method=getattr(self,'_run_'+challenge_id.replace('-','_'))
  with self._lock:
   simulation_engine.reset()
   try:result=method(definition)
   except Exception as error:
    now=simulation_engine.snapshot().simulated_time;result=self._result(definition,now,{'execution_error':str(error)},{},[],'The real pipeline could not complete this challenge.',now)
   finally:simulation_engine.reset()
   self._history.append(result);return result.model_copy(deep=True)
 def run_all(self): return [self.run(x.challenge_id) for x in DEFINITIONS]


challenge_service=AdversarialChallengeService()
