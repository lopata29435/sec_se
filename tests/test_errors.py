from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_not_found_item():
    r = client.get("/items/999")
    assert r.status_code == 404
    body = r.json()
    # RFC 7807 формат
    assert "type" in body
    assert "not-found" in body["type"]
    assert body["status"] == 404
    assert "correlation_id" in body


def test_validation_error():
    r = client.post("/items", json={"name": ""})
    assert r.status_code == 422
    body = r.json()
    # RFC 7807 формат
    assert "type" in body
    assert "validation" in body["type"]
    assert body["status"] == 422
