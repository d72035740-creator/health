from threading import RLock
from app.confounders.models import *
CONFUNDER_REVISION='confounder-v1'
def _bounded(x): return max(0.0,min(1.0,float(x)))
class ConfounderService:
    def __init__(self): self._lock=RLock(); self._latest=None
    def reset(self): self._latest=None
    def assess(self, attempt, temporal):
        vals={v.name:v.signed_normalized_delta for v in attempt.baseline_comparison.values}; left=[v for k,v in vals.items() if k.startswith('left_')]; right=[v for k,v in vals.items() if k.startswith('right_')]; lm=sum(map(abs,left))/len(left) if left else 0; rm=sum(map(abs,right))/len(right) if right else 0; total=lm+rm
        coherence=_bounded(1-abs(lm-rm)/(total+1e-9)); asym=_bounded(abs(lm-rm)/(total+1e-9)); side=DominantChangeSide.UNDETERMINED
        if total<0.05: side=DominantChangeSide.BALANCED
        elif lm>rm*1.2: side=DominantChangeSide.LEFT
        elif rm>lm*1.2: side=DominantChangeSide.RIGHT
        else: side=DominantChangeSide.BALANCED
        fs=attempt.quality_assessment.feature_summary; motion=_bounded(1-attempt.quality_assessment.dimension_scores.motion_score/100); contact=_bounded(1-attempt.quality_assessment.dimension_scores.contact_score/100); temps=[x.temperature_mean_c for x in fs.values()]; temp=_bounded(abs((temps[0]-temps[1]) if len(temps)>1 else 0)/2); transient=_bounded(1.0 if temporal and temporal.temporal_state.value in ('TRANSIENT_ELEVATION','RECOVERING_PATTERN') else 0.0)
        ex=[]
        ex.append({'code':'BILATERAL_CHANGE_COHERENT' if coherence>=.6 else 'UNILATERAL_PATTERN_DOMINANT','explanation':'Observed bilateral changes are coherent.' if coherence>=.6 else f'Observed change is asymmetric toward {side.value}.'})
        if temp>.25: ex.append({'code':'TEMPERATURE_SHIFT_PRESENT','explanation':'Observed temperature context changed alongside the measurement.'})
        if motion>.25: ex.append({'code':'RESIDUAL_MOTION_PRESENT','explanation':'Residual motion influence is possible.'})
        if contact>.25: ex.append({'code':'CONTACT_VARIABILITY_PRESENT','explanation':'Residual contact influence is possible.'})
        if transient>.5: ex.append({'code':'TRANSIENT_PATTERN_OBSERVED','explanation':'Temporal evidence is recovering/transient.'})
        if len(ex)==1: ex.append({'code':'NO_MAJOR_CONFOUNDER_IDENTIFIED','explanation':'No major observed contextual influence identified.'})
        self._latest=ConfounderAssessment(confounder_revision=CONFUNDER_REVISION,bilateral_coherence_score=coherence,unilateral_asymmetry_score=asym,dominant_change_side=side,systemic_bilateral_evidence=coherence,temperature_association_evidence=temp,residual_motion_evidence=motion,residual_contact_evidence=contact,transient_pattern_evidence=transient,explanations=ex); return self._latest
    def latest(self): return self._latest
confounder_service=ConfounderService()
from app.simulation.engine import simulation_engine
simulation_engine.register_reset_hook(confounder_service.reset)
