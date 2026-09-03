import math

from fastapi.testclient import TestClient

from app.domain.enums import ArmSide
from app.main import app
from app.runtime import runtime_service
from app.scenario import ScenarioType, scenario_provider
from app.simulation.bioimpedance.cole import ColeImpedanceModel
from app.simulation.bioimpedance.config import LEFT_ARM_PARAMETERS, RIGHT_ARM_PARAMETERS
from app.simulation.engine import simulation_engine
from app.simulation.sensors.models import SensorWindowRequest
from app.views.service import digital_twin_inspector_service


client = TestClient(app)
HIDDEN_KEYS = {"scenario_type", "scenario_id", "severity", "affected_arm", "r_zero_ohm", "r_infinity_ohm", "tau_seconds", "beta"}


def nested_keys(value):
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in nested_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in nested_keys(child)}
    return set()


def setup_function():
    simulation_engine.reset()


def arm(snapshot, name):
    return next(item for item in snapshot.arm_parameters if item.arm == name)


def test_base_and_baseline_effective_parameters_match_authoritative_config():
    snapshot = digital_twin_inspector_service.snapshot()
    assert arm(snapshot, "LEFT").base == LEFT_ARM_PARAMETERS.model_dump()
    assert arm(snapshot, "RIGHT").base == RIGHT_ARM_PARAMETERS.model_dump()
    assert arm(snapshot, "LEFT").effective == arm(snapshot, "LEFT").base
    assert arm(snapshot, "RIGHT").effective == arm(snapshot, "RIGHT").base


def test_effective_parameters_and_progression_match_scenario_provider():
    scenario_provider.select(ScenarioType.SLOW_UNILATERAL_SHIFT, ArmSide.LEFT)
    scenario_provider.start()
    simulation_engine.step(3 * 86_400)
    snapshot = digital_twin_inspector_service.snapshot()
    authoritative = scenario_provider.effective_parameters(ArmSide.LEFT, simulation_engine.snapshot().simulated_time, LEFT_ARM_PARAMETERS)
    assert arm(snapshot, "LEFT").effective == authoritative.model_dump()
    assert snapshot.scenario_ground_truth["synthetic_progression"] == scenario_provider.state().severity
    assert arm(snapshot, "LEFT").effective["r_zero_ohm"] > LEFT_ARM_PARAMETERS.r_zero_ohm
    assert arm(snapshot, "RIGHT").effective == RIGHT_ARM_PARAMETERS.model_dump()


def test_right_and_systemic_scenarios_modify_only_configured_arms():
    scenario_provider.select(ScenarioType.SLOW_UNILATERAL_SHIFT, ArmSide.RIGHT)
    scenario_provider.start(); simulation_engine.step(86_400)
    right = digital_twin_inspector_service.snapshot()
    assert arm(right, "LEFT").effective == LEFT_ARM_PARAMETERS.model_dump()
    assert arm(right, "RIGHT").effective["r_zero_ohm"] > RIGHT_ARM_PARAMETERS.r_zero_ohm
    simulation_engine.reset(); scenario_provider.select(ScenarioType.SYSTEMIC_BILATERAL_SHIFT); scenario_provider.start(); simulation_engine.step(86_400)
    systemic = digital_twin_inspector_service.snapshot()
    assert arm(systemic, "LEFT").effective["r_zero_ohm"] > LEFT_ARM_PARAMETERS.r_zero_ohm
    assert arm(systemic, "RIGHT").effective["r_zero_ohm"] > RIGHT_ARM_PARAMETERS.r_zero_ohm


def test_parameters_are_valid_and_preview_is_read_only():
    scenario_provider.select(ScenarioType.TRANSIENT_UNILATERAL_SHIFT, ArmSide.LEFT); scenario_provider.start(); simulation_engine.step(43_200)
    before = scenario_provider.state().as_dict().copy()
    snapshot = digital_twin_inspector_service.snapshot()
    after = scenario_provider.state().as_dict().copy()
    assert before == after
    for point in snapshot.parameter_evolution:
        for parameters in (point.left, point.right):
            assert parameters["r_zero_ohm"] > parameters["r_infinity_ohm"] > 0
            assert parameters["tau_seconds"] > 0
            assert 0 < parameters["beta"] <= 1


def test_inspector_spectrum_uses_authoritative_cole_equation():
    snapshot = digital_twin_inspector_service.snapshot()
    expected = ColeImpedanceModel(LEFT_ARM_PARAMETERS).impedance_at(5_000)
    actual = snapshot.model_prediction["LEFT"][0]
    assert math.isclose(actual.resistance_ohm, expected.real)
    assert math.isclose(actual.reactance_ohm, expected.imag)
    assert math.isclose(actual.magnitude_ohm, abs(expected))


def test_acquired_noise_and_processor_fit_are_separate_from_prediction():
    cycle = runtime_service.measure(SensorWindowRequest())
    snapshot = digital_twin_inspector_service.snapshot()
    assert snapshot.latest_acquired_sweep["measurement_attempt_id"] == cycle.attempt.attempt_id
    predicted = snapshot.model_prediction["LEFT"]
    acquired = snapshot.latest_acquired_sweep["left"]
    assert any(not math.isclose(a.magnitude_ohm, b["magnitude_ohm"], rel_tol=1e-8) for a, b in zip(predicted, acquired, strict=True))
    left_r0 = next(x for x in snapshot.fit_comparison if x.arm == "LEFT" and x.parameter == "R0")
    assert left_r0.processor_estimate == cycle.attempt.processed_features.left_cole_fit.r0_ohm
    assert snapshot.virtual_sensors.available is True
    assert snapshot.virtual_sensors.simulated_data is True


def test_engineering_truth_does_not_leak_to_observer_views_or_decision():
    inspector = client.get("/api/v1/views/digital-twin")
    assert inspector.status_code == 200
    assert "scenario_type" in nested_keys(inspector.json())
    for route in ("patient", "clinician"):
        assert HIDDEN_KEYS.isdisjoint(nested_keys(client.get(f"/api/v1/views/{route}").json()))
    cycle = runtime_service.measure(SensorWindowRequest())
    if cycle.attempt.ml_inference:
        assert HIDDEN_KEYS.isdisjoint(cycle.attempt.ml_inference.model_dump().keys())
    if cycle.attempt.decision_snapshot:
        assert HIDDEN_KEYS.isdisjoint(nested_keys(cycle.attempt.decision_snapshot.model_dump()))
