import anyio
from httpx import ASGITransport, Response, AsyncClient

from app.main import app


async def async_get(path: str) -> Response:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def get(path: str) -> Response:
    return anyio.run(async_get, path)


def test_health_returns_success() -> None:
    response = get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "aequor-api"}


def test_system_status_schema_and_explicit_unimplemented_states() -> None:
    response = get("/api/v1/system/status")
    assert response.status_code == 200
    body = response.json()
    assert body["backend"] == "READY"
    assert body["digital_patient_engine"] == "READY"
    assert body["data_provenance"] == "SIMULATED"

    future_engines = {
        "digital_twin",
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
    assert all(body[name] == "NOT_IMPLEMENTED" for name in future_engines)


def test_system_status_has_no_fake_medical_or_ml_result() -> None:
    body = get("/api/v1/system/status").json()
    forbidden = {"anomaly_score", "risk", "diagnosis", "adi", "clinical_state"}
    assert forbidden.isdisjoint(body)
