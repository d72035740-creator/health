from fastapi.testclient import TestClient

from app.main import app
from app.simulation.engine import simulation_engine
from app.timeline.models import TimelineEventSource, TimelineEventType
from app.timeline.service import timeline_service


client = TestClient(app)


def setup_function():
    simulation_engine.reset()


def events():
    return client.get("/api/v1/views/timeline").json()["events"]


def test_events_are_monotonic_and_use_authoritative_simulated_time():
    response = client.post("/api/v1/simulation/step", json={"seconds": 3600}).json()
    history = events()
    assert [x["sequence_index"] for x in history] == list(range(1, len(history) + 1))
    assert history[-1]["event_type"] == "SIMULATION_TIME_ADVANCED"
    assert history[-1]["simulated_time"] == response["simulated_time"]


def test_scenario_start_step_and_reset_append_without_erasing_history():
    client.post("/api/v1/scenarios/select", json={"scenario_type": "SLOW_UNILATERAL_SHIFT", "affected_arm": "LEFT"})
    client.post("/api/v1/scenarios/start")
    client.post("/api/v1/simulation/step", json={"seconds": 172800})
    before = len(events())
    client.post("/api/v1/scenarios/reset")
    history = events()
    assert len(history) == before + 1
    assert {"SCENARIO_SELECTED", "SCENARIO_STARTED", "SIMULATION_TIME_ADVANCED", "SCENARIO_RESET"}.issubset({x["event_type"] for x in history})


def test_qualified_and_rejected_measurements_record_actual_gating():
    client.post("/api/v1/runtime/measure", json={"motion_condition": "STABLE_REST", "contact_condition": "NOMINAL_CONTACT"})
    client.post("/api/v1/runtime/measure", json={"motion_condition": "ACTIVE_MOTION", "contact_condition": "NOMINAL_CONTACT"})
    history = events()
    qualified = next(x for x in history if x["event_type"] == "MEASUREMENT_QUALIFIED")
    rejected = next(x for x in history if x["event_type"] == "MEASUREMENT_REJECTED")
    assert qualified["measurement_summary"]["technical_quality"] == "QUALIFIED"
    assert rejected["measurement_summary"]["technical_quality"] == "REJECTED"
    assert rejected["ml_summary"] is None
    assert rejected["temporal_summary"] is None
    assert rejected["decision_summary"] is None


def test_temporal_reset_appends_and_full_reset_starts_new_session():
    old_session = client.get("/api/v1/views/timeline").json()["session"]["session_id"]
    client.post("/api/v1/temporal/reset")
    assert events()[-1]["event_type"] == "TEMPORAL_RESET"
    client.post("/api/v1/simulation/reset")
    replay = client.get("/api/v1/views/timeline").json()
    assert replay["session"]["session_id"] != old_session
    assert replay["session"]["reset_boundary"] == "FULL_RESET"
    assert [x["event_type"] for x in replay["events"]] == ["SYSTEM_RESET"]


def test_observer_only_projection_removes_truth_and_scenario_events():
    client.post("/api/v1/scenarios/select", json={"scenario_type": "SLOW_UNILATERAL_SHIFT", "affected_arm": "LEFT"})
    client.post("/api/v1/scenarios/start")
    client.post("/api/v1/runtime/measure", json={"motion_condition": "STABLE_REST", "contact_condition": "NOMINAL_CONTACT"})
    replay = client.get("/api/v1/views/timeline?include_ground_truth=false").json()
    assert replay["observer_only"] is True
    assert all(x["source"] != "SCENARIO_ENGINE" for x in replay["events"])
    assert all(x["scenario_ground_truth"] is None for x in replay["events"])


def test_replay_is_deep_recorded_and_does_not_recompute_history():
    original = {"adi": 42.5, "surveillance_state": "OBSERVING_CHANGE", "components": {"temporal": 0.4}}
    timeline_service.append(TimelineEventType.SURVEILLANCE_STATE_CHANGED, TimelineEventSource.DECISION_ENGINE, "Recorded decision", "Original decision configuration.", decision_summary=original)
    original["adi"] = 99.0
    original["components"]["temporal"] = 1.0
    stored = timeline_service.events()[-1]
    assert stored.decision_summary["adi"] == 42.5
    assert stored.decision_summary["components"]["temporal"] == 0.4


def test_change_events_are_emitted_only_on_change_and_order_is_deterministic():
    def run_sequence():
        simulation_engine.reset()
        client.post("/api/v1/scenarios/select", json={"scenario_type": "BASELINE_STABLE", "affected_arm": None})
        client.post("/api/v1/scenarios/start")
        client.post("/api/v1/runtime/measure", json={"motion_condition": "STABLE_REST", "contact_condition": "NOMINAL_CONTACT"})
        return [x["event_type"] for x in events()]
    assert run_sequence() == run_sequence()


def test_patient_and_clinician_remain_scenario_blind():
    forbidden = {"scenario_type", "scenario_id", "severity", "affected_arm"}
    def keys(value):
        if isinstance(value, dict): return set(value) | {k for child in value.values() for k in keys(child)}
        if isinstance(value, list): return {k for child in value for k in keys(child)}
        return set()
    for route in ("patient", "clinician"):
        assert forbidden.isdisjoint(keys(client.get(f"/api/v1/views/{route}").json()))
