from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from app.temporal.service import TemporalService, TemporalHistoryError
from app.temporal.models import TemporalEvidenceState
from app.confounders.service import ConfounderService

def ml(z): return SimpleNamespace(reconstruction_error_mse=1.0, novelty_z=z, model_novelty_score=.5, model_revision='aequor-ae-v1', status='READY')
def test_time_aware_ewma_and_order():
    s=TemporalService(); t=datetime(2026,1,1,tzinfo=timezone.utc); s.observe(attempt_id='a',simulated_time=t,ml=ml(2)); a=s.observe(attempt_id='b',simulated_time=t+timedelta(days=2),ml=ml(0)); assert 0<a.ewma_novelty<2
    try: s.observe(attempt_id='c',simulated_time=t,ml=ml(1)); assert False
    except TemporalHistoryError: pass
def test_persistence_requires_count_and_span_and_reset():
    s=TemporalService(); t=datetime(2026,1,1,tzinfo=timezone.utc)
    for i in range(3): a=s.observe(attempt_id=str(i),simulated_time=t+timedelta(days=i),ml=ml(2))
    assert a.temporal_state is TemporalEvidenceState.SUSTAINED_ELEVATION; assert a.persistence_duration_days==2
    s.reset(); assert s.assessment().observation_count==0
def test_confounder_direction_is_observed_only():
    c=ConfounderService(); base=SimpleNamespace(baseline_comparison=SimpleNamespace(values=[SimpleNamespace(name='left_x',signed_normalized_delta=3),SimpleNamespace(name='right_x',signed_normalized_delta=.1)]),quality_assessment=SimpleNamespace(feature_summary={'left':SimpleNamespace(temperature_mean_c=30),'right':SimpleNamespace(temperature_mean_c=30)},dimension_scores=SimpleNamespace(motion_score=100,contact_score=100)))
    out=c.assess(base,None); assert out.dominant_change_side.value=='LEFT'; assert 0<=out.unilateral_asymmetry_score<=1
