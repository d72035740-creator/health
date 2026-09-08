from fastapi.testclient import TestClient

from app.baseline.service import baseline_service
from app.challenges.models import ChallengeStatus
from app.challenges.service import challenge_service
from app.main import app
from app.runtime import runtime_service
from app.simulation.engine import simulation_engine


client=TestClient(app)
def setup_function():simulation_engine.reset()


def test_active_motion_verdict_uses_real_runtime_gating():
 result=challenge_service.run('active-motion');e=result.observed_evidence
 assert result.status is ChallengeStatus.PASS
 assert e.observations['quality']=='REJECTED'
 assert e.observations['pipeline_status']=='BLOCKED_BY_QUALITY'
 assert all(e.invariant_checks.values())


def test_poor_contact_and_posture_use_real_quality_engine():
 for challenge in ('poor-contact','posture-transition'):
  result=challenge_service.run(challenge)
  assert result.observed_evidence.observations['rejection_reasons']
  assert result.observed_evidence.observations['bis_ran'] is False
  assert result.status is ChallengeStatus.PASS


def test_one_transient_cannot_pass_if_persistent_state_reached():
 result=challenge_service.run('transient-spike');e=result.observed_evidence
 assert e.observations['spike_state']=='OBSERVING_CHANGE'
 assert e.invariant_checks['single_spike_not_persistent'] is True
 assert result.status is ChallengeStatus.PASS


def test_systemic_uses_observed_confounder_evidence():
 result=challenge_service.run('systemic-shift');e=result.observed_evidence.observations
 assert e['systemic_run']['systemic']>e['unilateral_reference']['systemic']
 assert e['systemic_evidence_margin']>=.2
 assert result.status is ChallengeStatus.PASS


def test_arm_symmetry_reverses_observed_direction():
 result=challenge_service.run('arm-symmetry');e=result.observed_evidence.observations
 assert e['left_run']['side']=='LEFT' and e['right_run']['side']=='RIGHT'
 assert e['adi_absolute_difference']<=e['engineering_tolerance']
 assert result.status is ChallengeStatus.PASS


def test_model_unavailable_has_no_fake_score_or_downstream_updates():
 result=challenge_service.run('model-unavailable');e=result.observed_evidence
 assert e.observations['pipeline_status']=='ML_UNAVAILABLE'
 assert e.observations['ml_result'] is None
 assert all(e.invariant_checks.values())
 assert e.observations['artifact_modified'] is False


def test_leakage_challenge_structurally_inspects_real_contracts():
 result=challenge_service.run('label-leakage');e=result.observed_evidence
 assert e.observations['ground_truth_leakage']=='NONE DETECTED'
 assert {'ml_input_names','temporal_observation','decision_snapshot','patient_view','clinician_view'}==set(e.observations['inspected_contracts'])
 assert e.observations['ml_input_dimension']==34
 assert all(e.invariant_checks.values())


def test_scenario_reset_does_not_downgrade_without_observation():
 result=challenge_service.run('scenario-reset');e=result.observed_evidence.observations
 assert e['state_before_reset']=='PERSISTENT_DEVIATION'
 assert e['state_immediately_after_reset']==e['state_before_reset']
 assert e['decision_time_after']==e['decision_time_before']
 assert e['new_observation_after_reset'] is False


def test_stale_decision_is_not_attributed_to_rejected_cycle():
 result=challenge_service.run('stale-decision');e=result.observed_evidence
 assert e.observations['rejected_pipeline_status']=='BLOCKED_BY_QUALITY'
 assert e.observations['decision_updated'] is False
 assert e.observations['rejected_cycle_adi'] is None
 assert all(e.invariant_checks.values())


def test_status_is_evidence_derived_and_inconclusive_supported():
 assert challenge_service._status({'observed':True}) is ChallengeStatus.PASS
 assert challenge_service._status({'observed':False}) is ChallengeStatus.FAIL
 assert challenge_service._status({'not_observable':None}) is ChallengeStatus.INCONCLUSIVE


def test_run_all_isolates_state_and_records_history():
 before=len(challenge_service.history());results=challenge_service.run_all()
 assert len(results)==10 and len(challenge_service.history())==before+10
 assert baseline_service.snapshot().state.value=='UNINITIALIZED'
 assert runtime_service.snapshot() is None
 assert client.get('/api/v1/challenges/status').status_code==200


def test_patient_and_clinician_views_contain_no_challenge_metadata():
 challenge_service.run('active-motion')
 for route in ('patient','clinician'):
  body=client.get(f'/api/v1/views/{route}').json()
  assert 'challenge_id' not in str(body) and 'challenge_type' not in str(body)
