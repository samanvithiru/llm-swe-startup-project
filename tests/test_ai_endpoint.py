
"""Test the AI preference API endpoint."""

from fastapi.testclient import TestClient
from app.server import app

client = TestClient(app)


# Check that the AI endpoint returns a preference
def test_ai_preference_endpoint(monkeypatch):
    def fake_ai(instruction):
        return {"preference": "preserve_center"}

    monkeypatch.setattr(
        "app.server.get_ai_preference",
        fake_ai
    )

    response = client.post(
        "/api/ai-preference",
        json={"instruction": "Keep the center dancers in place"}
    )

    assert response.status_code == 200
    assert response.json() == {"preference": "preserve_center"}


# Check that empty instructions are rejected
def test_empty_ai_instruction():
    response = client.post(
        "/api/ai-preference",
        json={"instruction": ""}
    )

    assert response.status_code == 400


# Check that API failures are handled
def test_ai_failure(monkeypatch):
    def fake_ai(instruction):
        raise ConnectionError("AI unavailable")

    monkeypatch.setattr(
        "app.server.get_ai_preference",
        fake_ai
    )

    response = client.post(
        "/api/ai-preference",
        json={"instruction": "Minimize movement"}
    )

    assert response.status_code == 503
