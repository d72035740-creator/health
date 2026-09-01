from fastapi.testclient import TestClient

from app.main import app


def test_virtual_sensor_config_and_window_api() -> None:
    with TestClient(app) as client:
        config = client.get("/api/v1/virtual-sensors/config")
        assert config.status_code == 200
        assert config.json()["imu_sample_rate_hz"] == 50
        window = client.post("/api/v1/virtual-sensors/window", json={"motion_condition":"POSTURE_TRANSITION", "contact_condition":"POOR_CONTACT", "temperature_offset_c":0.5})
    assert window.status_code == 200
    body = window.json()
    assert body["left"]["arm_side"] == "LEFT" and body["right"]["arm_side"] == "RIGHT"
    assert body["qualification"] == "RAW_UNQUALIFIED" and body["provenance"] == "SIMULATED"
    serialized = str(body).lower()
    for forbidden in ("quality_score", "accepted", "rejected", "anomaly", "diagnosis", "risk", "adi"):
        assert forbidden not in serialized


def test_system_status_marks_raw_sources_ready_only() -> None:
    with TestClient(app) as client: body = client.get("/api/v1/system/status").json()
    assert body["virtual_imu"] == body["virtual_temperature"] == body["virtual_contact"] == "READY"
    assert body["quality_engine"] == "READY"
    assert body["signal_processing"] == "READY"
