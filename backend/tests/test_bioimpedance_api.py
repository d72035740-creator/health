from typing import Any

import anyio
from httpx import ASGITransport, AsyncClient, Response

from app.main import app
from app.simulation.engine import simulation_engine


async def request(method: str, path: str) -> Response:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path)


def call(method: str, path: str) -> Response:
    return anyio.run(request, method, path)


def all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for child in value.values() for key in all_keys(child)}
    if isinstance(value, list):
        return {key for child in value for key in all_keys(child)}
    return set()


def setup_function() -> None:
    simulation_engine.reset()


def test_config_exposes_expected_engineering_metadata() -> None:
    response = call("GET", "/api/v1/bioimpedance/config")
    assert response.status_code == 200
    body = response.json()
    assert body["frequencies_hz"] == [5_000, 10_000, 20_000, 50_000, 100_000, 200_000]
    assert body["model_name"] == "Cole Digital Twin"
    assert body["model_revision"] == "cole-v1"
    assert body["provenance"] == "SIMULATED"
    assert body["noise"]["enabled"] is True


def test_sweep_endpoint_returns_bilateral_raw_schema_without_future_results() -> None:
    response = call("POST", "/api/v1/bioimpedance/sweep")
    assert response.status_code == 200
    body = response.json()
    assert body["left"]["arm_side"] == "LEFT"
    assert body["right"]["arm_side"] == "RIGHT"
    assert body["qualification"] == "RAW_UNQUALIFIED"
    assert len(body["left"]["points"]) == len(body["right"]["points"]) == 6

    forbidden = {
        "diagnosis",
        "risk",
        "adi",
        "ml_score",
        "anomaly_score",
        "accepted",
        "high_quality",
        "clinically_valid",
    }
    assert forbidden.isdisjoint({key.lower() for key in all_keys(body)})


def test_system_status_reports_only_completed_phase_two_subsystem_ready() -> None:
    body = call("GET", "/api/v1/system/status").json()
    assert body["digital_patient_engine"] == "READY"
    assert body["bioimpedance_digital_twin"] == "READY"
    assert body["digital_twin"] == "NOT_IMPLEMENTED"
    future = {
        "virtual_imu",
        "virtual_temperature",
        "virtual_contact",
        "quality_engine",
        "signal_processing",
        "baseline_engine",
        "ml_engine",
        "temporal_engine",
        "confounder_engine",
        "decision_engine",
    }
    assert all(body[name] == "NOT_IMPLEMENTED" for name in future)

