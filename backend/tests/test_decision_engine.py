from datetime import datetime, timezone
from types import SimpleNamespace
from app.decision.config import WEIGHTS
from app.decision.models import SurveillanceState
from app.decision.service import DecisionService

def attempt(deltas=(0.,)*34, z=0., persistence=0., unilateral=0., systemic=0., transient=0.):
 return SimpleNamespace(simulated_time=datetime(2026,1,1,tzinfo=timezone.utc),baseline_comparison=SimpleNamespace(values=[SimpleNamespace(signed_normalized_delta=x) for x in deltas]),ml_inference=SimpleNamespace(novelty_z=z,model_revision='aequor-ae-v1'),temporal_assessment=SimpleNamespace(ewma_novelty=z,persistence_duration_days=persistence,temporal_state=SimpleNamespace(value='RISING_PERSISTENT_PATTERN'),elevated_observation_count=3,observation_count=5),confounder_assessment=SimpleNamespace(unilateral_asymmetry_score=unilateral,systemic_bilateral_evidence=systemic,transient_pattern_evidence=transient,residual_motion_evidence=0,residual_contact_evidence=0,dominant_change_side=SimpleNamespace(value='LEFT')))
def test_adi_bounds_weights_and_modifiers():
 s=DecisionService(); assert sum(WEIGHTS.values())==1
 low=s.evaluate(attempt()); high=s.evaluate(attempt((20,)*34,8,7,1)); systemic=s.evaluate(attempt((20,)*34,8,7,1,1)); transient=s.evaluate(attempt((20,)*34,8,7,1,0,1)); assert 0<=low.adi<=100 and 0<=high.adi<=100 and high.adi>=low.adi and systemic.adi<=high.adi and transient.adi<=high.adi
def test_single_high_cannot_be_persistent_or_review():
 s=DecisionService(); a=attempt((20,)*34,8,0,1); a.temporal_assessment.elevated_observation_count=1; a.temporal_assessment.observation_count=1; out=s.evaluate(a); assert out.surveillance_state not in (SurveillanceState.PERSISTENT_DEVIATION,SurveillanceState.CLINICAL_REVIEW_RECOMMENDED)
def test_baseline_missing_is_calibrating_and_null_adi():
 s=DecisionService(); a=attempt(); a.baseline_comparison=None; out=s.evaluate(a); assert out.adi is None and out.surveillance_state is SurveillanceState.CALIBRATING
