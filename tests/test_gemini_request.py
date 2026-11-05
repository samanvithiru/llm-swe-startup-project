
"""Test Gemini AI preference requests."""

import pytest
from types import SimpleNamespace

from app.gemini_request import get_gemini_preference


# Test a successful Gemini response
def test_successful_gemini_request():
    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(
                text='{"preference": "preserve_center"}'
            )

    fake_client = SimpleNamespace(models=FakeModels())

    result = get_gemini_preference(
        "Keep the center dancers in place",
        client=fake_client
    )

    assert result == {"preference": "preserve_center"}


# Test that the instruction is sent to Gemini
def test_instruction_is_sent(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    calls = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                text='{"preference": "minimize_changes"}'
            )

    fake_client = SimpleNamespace(models=FakeModels())

    get_gemini_preference(
        "Minimize dancer movement",
        client=fake_client
    )

    assert calls[0]["model"] == "gemini-3.5-flash-lite"
    assert len(calls) == 1
    assert "Minimize dancer movement" in str(calls[0]["contents"])


# Test that empty instructions are rejected
def test_empty_instruction():
    with pytest.raises(ValueError):
        get_gemini_preference("   ", client=None)


# Test that invalid Gemini responses are rejected
def test_invalid_gemini_response():
    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(text="Invalid response")

    fake_client = SimpleNamespace(models=FakeModels())

    with pytest.raises(ValueError):
        get_gemini_preference(
            "Keep dancers centered",
            client=fake_client
        )


# Test that Gemini API errors are handled
def test_gemini_api_failure():
    class FakeModels:
        def generate_content(self, **kwargs):
            raise ConnectionError("Gemini unavailable")

    fake_client = SimpleNamespace(models=FakeModels())

    with pytest.raises(ConnectionError):
        get_gemini_preference(
            "Minimize movement",
            client=fake_client
        )


def test_model_can_be_configured(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "team-selected-model")
    calls = []

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text='{"preference":"minimize_changes"}')

    get_gemini_preference("Minimize movement", client=SimpleNamespace(models=FakeModels()))
    assert calls[0]["model"] == "team-selected-model"
