import json

from fastapi.testclient import TestClient

from app.main import app
from app.ml.runtime import ml_runtime
from app.simulation.engine import simulation_engine


client = TestClient(app)
FORBIDDEN_TRUTH = {"scenario_type", "scenario_id", "severity", "affected_arm"}


def nested_keys(value):
    if isinstance(value, dict): return set(value) | {k for child in value.values() for k in nested_keys(child)}
    if isinstance(value, list): return {k for child in value for k in nested_keys(child)}
    return set()


def setup_function(): simulation_engine.reset()


def test_privacy_reports_local_tflite_and_no_cloud_dependencies():
    body = client.get("/api/v1/views/privacy").json()
    assert body["model_execution"]["execution_location"] == "LOCAL PROTOTYPE PROCESS"
    assert body["model_execution"]["artifact_type"] == "TFLite"
    assert body["model_execution"]["quantization"] == "INT8"
    assert body["network_dependencies"]["cloud_inference_required"] is False
    assert body["network_dependencies"]["external_model_api_required"] is False
    assert body["network_dependencies"]["internet_required_for_core_inference"] is False
    assert body["external_services"] == []


def test_model_metadata_matches_actual_loaded_artifact():
    body = client.get("/api/v1/views/privacy").json()["model_execution"]
    actual = ml_runtime.status()
    assert body["model_name"] == actual["model_name"]
    assert body["revision"] == actual["model_revision"]
    assert body["file_size_bytes"] == actual["model_size_bytes"]
    assert body["runtime"] == actual["runtime"]
    assert body["loaded"] == actual["loaded"]
    assert body["input_dimension"] == 34


def test_storage_and_reset_claims_match_in_memory_implementation():
    body = client.get("/api/v1/views/privacy").json()
    locations = {x["data"]: x for x in body["storage_locations"]}
    assert locations["Personalized baseline"]["location"] == "Process memory"
    assert "full reset" in locations["Personalized baseline"]["lifetime"].lower()
    assert locations["INT8 TFLite model and metadata"]["location"] == "Local disk"
    assert "all in-memory state" in body["retention_behavior"]["process_restart_clears"][0]
    assert "new timeline replay session" in body["retention_behavior"]["full_reset_boundary"][0]


def test_ground_truth_classified_engineering_only_and_observer_views_blind():
    body = client.get("/api/v1/views/privacy").json()
    classification = next(x for x in body["data_sources"] if x["classification"] == "ENGINEERING-ONLY GROUND TRUTH")
    assert "scenario type" in classification["items"]
    for route in ("patient", "clinician"):
        assert FORBIDDEN_TRUTH.isdisjoint(nested_keys(client.get(f"/api/v1/views/{route}").json()))


def test_security_claims_are_explicitly_unimplemented_not_positive_claims():
    body = client.get("/api/v1/views/privacy").json()
    not_implemented = " ".join(body["not_yet_implemented"]).lower()
    assert "encrypted persistent clinical database" in not_implemented
    assert "regulatory compliance framework" in not_implemented
    positive = body.copy(); positive.pop("not_yet_implemented"); text = json.dumps(positive).lower()
    for unsupported in ("hipaa compliant", "gdpr certified", "secure enclave", "end-to-end encryption", "hardware secure element"):
        assert unsupported not in text


def test_hardware_is_future_and_missing_model_behavior_is_honest():
    body = client.get("/api/v1/views/privacy").json()
    assert body["planned_hardware_deployment"]["status"].startswith("FUTURE / TARGET")
    assert "NOT CURRENTLY IMPLEMENTED" in body["planned_hardware_deployment"]["status"]
    assert body["model_execution"]["missing_behavior"].startswith("ML_UNAVAILABLE")
    assert "no fallback score" in body["model_execution"]["missing_behavior"]
