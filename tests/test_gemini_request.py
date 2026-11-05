
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



# Additional Gemini coverage tests

import app.gemini_request as gemini_module


# Simulate Gemini HTTP errors without calling the real API
class FakeServerError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(f"Gemini server error: {code}")


# Test that a missing API key is rejected
def test_missing_gemini_api_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        get_gemini_preference(
            "Minimize movement"
        )


# Test that Gemini client is created with the API key
def test_gemini_client_created_from_environment(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")

    created_clients = []

    class FakeModels:
        def generate_content(self, **kwargs):
            return SimpleNamespace(
                text='{"preference": "preserve_center"}'
            )

    def fake_client_factory(api_key):
        created_clients.append(api_key)
        return SimpleNamespace(models=FakeModels())

    monkeypatch.setattr(
        gemini_module.genai,
        "Client",
        fake_client_factory
    )

    result = get_gemini_preference(
        "Keep the center dancers in place"
    )

    assert created_clients == ["fake-test-key"]
    assert result == {"preference": "preserve_center"}


# Test retrying each supported temporary server error
@pytest.mark.parametrize("error_code", [500, 502, 503, 504])
def test_gemini_retries_temporary_errors(
    monkeypatch, error_code
):
    monkeypatch.setattr(
        gemini_module, "ServerError", FakeServerError
    )

    delays = []
    monkeypatch.setattr(
        gemini_module.time, "sleep", delays.append
    )

    attempts = []

    class FakeModels:
        def generate_content(self, **kwargs):
            attempts.append(kwargs)

            if len(attempts) == 1:
                raise FakeServerError(error_code)

            return SimpleNamespace(
                text='{"preference": "minimize_changes"}'
            )

    client = SimpleNamespace(models=FakeModels())

    result = get_gemini_preference(
        "Minimize dancer movement",
        client=client
    )

    assert result == {"preference": "minimize_changes"}
    assert len(attempts) == 2
    assert delays == [1]


# Test that permanent errors are NOT retried
def test_gemini_does_not_retry_permanent_errors(monkeypatch):
    monkeypatch.setattr(
        gemini_module, "ServerError", FakeServerError
    )

    delays = []
    monkeypatch.setattr(
        gemini_module.time, "sleep", delays.append
    )

    attempts = []

    class FakeModels:
        def generate_content(self, **kwargs):
            attempts.append(kwargs)
            raise FakeServerError(400)

    client = SimpleNamespace(models=FakeModels())

    with pytest.raises(FakeServerError) as error:
        get_gemini_preference(
            "Minimize movement",
            client=client
        )

    assert error.value.code == 400
    assert len(attempts) == 1
    assert delays == []


# Test successful response after two failures
def test_gemini_succeeds_on_third_attempt(monkeypatch):
    monkeypatch.setattr(
        gemini_module, "ServerError", FakeServerError
    )

    delays = []
    monkeypatch.setattr(
        gemini_module.time, "sleep", delays.append
    )

    attempts = []

    class FakeModels:
        def generate_content(self, **kwargs):
            attempts.append(kwargs)

            if len(attempts) < 3:
                raise FakeServerError(503)

            return SimpleNamespace(
                text='{"preference": "preserve_center"}'
            )

    client = SimpleNamespace(models=FakeModels())

    result = get_gemini_preference(
        "Preserve the center",
        client=client
    )

    assert result == {"preference": "preserve_center"}
    assert len(attempts) == 3
    assert delays == [1, 2]


# Test that retrying stops after three failures
def test_gemini_stops_after_three_failures(monkeypatch):
    monkeypatch.setattr(
        gemini_module, "ServerError", FakeServerError
    )

    delays = []
    monkeypatch.setattr(
        gemini_module.time, "sleep", delays.append
    )

    attempts = []

    class FakeModels:
        def generate_content(self, **kwargs):
            attempts.append(kwargs)
            raise FakeServerError(503)

    client = SimpleNamespace(models=FakeModels())

    with pytest.raises(FakeServerError) as error:
        get_gemini_preference(
            "Minimize movement",
            client=client
        )

    assert error.value.code == 503
    assert len(attempts) == 3
    assert delays == [1, 2]


# Test empty and None instructions
@pytest.mark.parametrize("instruction", ["", None])
def test_gemini_rejects_missing_instruction(instruction):
    with pytest.raises(ValueError):
        get_gemini_preference(
            instruction,
            client=None
        )

