
import pytest
from types import SimpleNamespace

from app.openai_request import get_ai_preference


# Test a successful AI request
def test_successful_request():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(
                output_text='{"preference": "preserve_center"}'
            )

    fake_client = SimpleNamespace(responses=FakeResponses())

    result = get_ai_preference(
        "Keep the middle dancers in place",
        client=fake_client
    )

    assert result == {"preference": "preserve_center"}


# Test that the user's instruction is sent to the AI
def test_instruction_is_sent():
    calls = []

    class FakeResponses:
        def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                output_text='{"preference": "minimize_changes"}'
            )

    fake_client = SimpleNamespace(responses=FakeResponses())

    get_ai_preference("Minimize movement", client=fake_client)

    assert len(calls) == 1
    assert "Minimize movement" in str(calls[0]["input"])


# Test that empty instructions are rejected
def test_empty_instruction():
    with pytest.raises(ValueError):
        get_ai_preference("   ", client=None)


# Test that invalid AI responses are rejected
def test_invalid_ai_response():
    class FakeResponses:
        def create(self, **kwargs):
            return SimpleNamespace(output_text="Invalid response")

    fake_client = SimpleNamespace(responses=FakeResponses())

    with pytest.raises(ValueError):
        get_ai_preference("Keep dancers centered", client=fake_client)


# Test that API errors are passed along
def test_api_failure():
    class FakeResponses:
        def create(self, **kwargs):
            raise ConnectionError("API unavailable")

    fake_client = SimpleNamespace(responses=FakeResponses())

    with pytest.raises(ConnectionError):
        get_ai_preference("Minimize movement", client=fake_client)
