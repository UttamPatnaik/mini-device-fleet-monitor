from fastapi.testclient import TestClient

from src.main import app


client = TestClient(app)


def test_register_device():
    resp = client.post("/devices", json={"id": "t1", "name": "Test 1"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == "t1"
    assert body["name"] == "Test 1"
    assert body["status"] == "OFFLINE"
    assert body["last_heartbeat"] is None


def test_duplicate_registration_returns_409():
    client.post("/devices", json={"id": "dup", "name": "Dup"})
    resp = client.post("/devices", json={"id": "dup", "name": "Dup2"})
    assert resp.status_code == 409


def test_list_devices():
    client.post("/devices", json={"id": "list1", "name": "List 1"})
    resp = client.get("/devices")
    assert resp.status_code == 200
    ids = [d["id"] for d in resp.json()]
    assert "list1" in ids


def test_get_device_details():
    client.post("/devices", json={"id": "detail1", "name": "Detail 1"})
    resp = client.get("/devices/detail1")
    assert resp.status_code == 200
    assert resp.json()["id"] == "detail1"


def test_get_unknown_device_returns_404():
    resp = client.get("/devices/does-not-exist")
    assert resp.status_code == 404


def test_heartbeat_unknown_device_returns_404():
    resp = client.post(
        "/devices/nope/heartbeat",
        json={"timestamp": "2026-09-30T10:30:00Z", "status": "OK"},
    )
    assert resp.status_code == 404


def test_heartbeat_naive_timestamp_returns_422():
    client.post("/devices", json={"id": "hbtest", "name": "HB"})
    resp = client.post(
        "/devices/hbtest/heartbeat",
        json={"timestamp": "2026-09-30T10:30:00", "status": "OK"},
    )
    assert resp.status_code == 422


def test_empty_summary():
    resp = client.get("/summary")
    assert resp.status_code == 200
    assert "total" in resp.json()
    assert "online" in resp.json()
    assert "offline" in resp.json()