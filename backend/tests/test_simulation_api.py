import anyio
from httpx import ASGITransport, AsyncClient, Response

from app.main import app
from app.simulation.engine import DEFAULT_SPEED_MULTIPLIER, simulation_engine


async def request(method: str, path: str, json: dict[str, float] | None = None) -> Response:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, json=json)


def call(method: str, path: str, json: dict[str, float] | None = None) -> Response:
    return anyio.run(request, method, path, json)


def setup_function() -> None:
    simulation_engine.reset()
    simulation_engine.set_speed(DEFAULT_SPEED_MULTIPLIER)


def test_simulation_snapshot_and_lifecycle_endpoints() -> None:
    initial = call("GET", "/api/v1/simulation")
    assert initial.status_code == 200
    assert initial.json()["patient"]["synthetic"] is True
    assert initial.json()["data_provenance"] == "SIMULATED"

    started = call("POST", "/api/v1/simulation/start")
    assert started.status_code == 200
    assert started.json()["lifecycle"] == "RUNNING"

    paused = call("POST", "/api/v1/simulation/pause")
    assert paused.json()["lifecycle"] == "PAUSED"

    resumed = call("POST", "/api/v1/simulation/resume")
    assert resumed.json()["lifecycle"] == "RUNNING"


def test_invalid_transition_returns_explicit_conflict() -> None:
    response = call("POST", "/api/v1/simulation/resume")
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "INVALID_SIMULATION_LIFECYCLE"


def test_speed_validation_and_manual_step_conflict() -> None:
    invalid_speed = call(
        "PATCH",
        "/api/v1/simulation/speed",
        {"speed_multiplier": 100_000},
    )
    assert invalid_speed.status_code == 422

    call("POST", "/api/v1/simulation/start")
    running_step = call("POST", "/api/v1/simulation/step", {"seconds": 60})
    assert running_step.status_code == 409


def test_system_status_marks_only_digital_patient_as_newly_ready() -> None:
    body = call("GET", "/api/v1/system/status").json()
    assert body["digital_patient_engine"] == "READY"
    assert body["digital_twin"] == "NOT_IMPLEMENTED"
    future_engines = {
        "quality_engine",
        "signal_processing",
        "baseline_engine",
        "ml_engine",
        "temporal_engine",
        "confounder_engine",
        "decision_engine",
    }
    assert all(body[name] == "NOT_IMPLEMENTED" for name in future_engines)

