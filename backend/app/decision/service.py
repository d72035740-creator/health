from threading import RLock
from app.decision.models import *
from app.decision.config import *
def b(x): return max(0.,min(1.,float(x)))
class DecisionService:
 def __init__(self): self._lock=RLock(); self.reset()
 def reset(self):
  with self._lock: self._state=SurveillanceState.CALIBRATING; self._latest=None; self._history=[]
 def evaluate(self,attempt):
  with self._lock:
   if attempt.baseline_comparison is None: return self._snapshot(attempt.simulated_time,None,None,None,attempt)
   d=sorted((min(CLIP,abs(v.signed_normalized_delta))/CLIP for v in attempt.baseline_comparison.values),reverse=True)[:TOP_K]; pd=b(sum(d)/len(d) if d else 0); ml=b((attempt.ml_inference.novelty_z+2)/10) if attempt.ml_inference else 0; t=attempt.temporal_assessment; temporal=b((abs(t.ewma_novelty or 0)/8)*.5+(t.persistence_duration_days/7)*.5) if t else 0; c=attempt.confounder_assessment; uni=b(c.unilateral_asymmetry_score if c else 0); systemic=b(c.systemic_bilateral_evidence if c else 0); transient=b(c.transient_pattern_evidence if c else 0); tech=b((c.residual_motion_evidence+c.residual_contact_evidence)/2 if c else 0); raw=100*sum((WEIGHTS['personalized_deviation']*pd,WEIGHTS['ml_novelty']*ml,WEIGHTS['temporal']*temporal,WEIGHTS['unilateral_pattern']*uni)); adi=max(0,min(100,raw*(1-.35*systemic)*(1-.35*transient)*(1-.15*tech))); state=self._next(adi,t); codes=[]
   if pd>.4: codes.append('PERSONAL_DEVIATION_ELEVATED')
   if ml>.4: codes.append('ML_NOVELTY_ELEVATED')
   if t and t.persistence_duration_days>=2: codes.append('TEMPORAL_PERSISTENCE_PRESENT')
   if uni>.5: codes.append('UNILATERAL_PATTERN_DOMINANT')
   if systemic>.6: codes.append('SYSTEMIC_PATTERN_REDUCES_UNILATERAL_EVIDENCE')
   if transient>.5: codes.append('TRANSIENT_PATTERN_REDUCES_PERSISTENCE_EVIDENCE')
   snap=self._snapshot(attempt.simulated_time,adi,{'personalized_deviation':pd,'ml_novelty':ml,'temporal':temporal,'unilateral_pattern':uni},{'systemic':systemic,'transient':transient,'residual_technical':tech},attempt,state,codes); self._latest=snap; return snap
 def _next(self,adi,t):
  persistent=t and t.temporal_state.value in ('SUSTAINED_ELEVATION','RISING_PERSISTENT_PATTERN') and t.elevated_observation_count>=3 and t.persistence_duration_days>=2
  if adi>=REVIEW and persistent and t.persistence_duration_days>=MIN_REVIEW_DAYS and t.observation_count>=MIN_REVIEW_COUNT: return SurveillanceState.CLINICAL_REVIEW_RECOMMENDED
  if adi>=PERSISTENT and persistent:return SurveillanceState.PERSISTENT_DEVIATION
  if adi>=OBSERVE:return SurveillanceState.OBSERVING_CHANGE
  return SurveillanceState.WITHIN_PERSONAL_BASELINE
 def _snapshot(self,time,adi,components,modifiers,attempt,state=None,codes=None):
  state=state or (SurveillanceState.CALIBRATING if adi is None else self._state); self._state=state; return DecisionSnapshot(decision_engine_name='Aequor Surveillance Decision Engine',adi_revision='adi-v1',state_machine_revision='surveillance-v1',simulated_time=time,adi=adi,components=components,modifiers=modifiers,surveillance_state=state,dominant_observed_side=attempt.confounder_assessment.dominant_change_side.value if attempt.confounder_assessment else None,explanation_codes=codes or [],explanations=['Prototype research index; not a disease probability.'],evidence_revisions={'feature_revision':'bis-features-v1','baseline_revision':'baseline-v1','model_revision':attempt.ml_inference.model_revision if attempt.ml_inference else '','temporal_revision':'temporal-v1','confounder_revision':'confounder-v1'})
 def latest(self): return self._latest
 def history(self): return list(self._history)
decision_service=DecisionService()
from app.simulation.engine import simulation_engine
simulation_engine.register_reset_hook(decision_service.reset)
