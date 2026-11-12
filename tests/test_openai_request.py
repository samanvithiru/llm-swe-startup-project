
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

    fake_client = SimpleNamespace(
        responses=FakeResponses()
    )

    instructions = [
        "Minimize movement",
        "Keep the center dancers!",
        "Minimize changes\nPreserve symmetry"
    ]

    for instruction in instructions:
        result = get_ai_preference(
            instruction,
            client=fake_client
        )

        assert result["preference"] == "minimize_changes"

    assert len(calls) == len(instructions)

    for call, instruction in zip(calls, instructions):
        assert call["input"] == instruction
        assert call["model"] == "gpt-4.1-mini"

        system_prompt = call["instructions"]

        assert "minimize_changes" in system_prompt
        assert "preserve_center" in system_prompt
        assert "JSON" in system_prompt



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
