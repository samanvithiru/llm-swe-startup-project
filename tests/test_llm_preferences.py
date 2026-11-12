
import pytest

from app.llm_preferences import interpret_with_llm


# Check that the LLM can return a supported preference
def test_valid_llm_response():
    def fake_llm(instruction):
        return {"preference": "preserve_center"}

    result = interpret_with_llm(
        "Keep the middle dancers in place",
        llm_call=fake_llm
    )

    assert result["preference"] == "preserve_center"


# Check that unsupported preferences are rejected
def test_unsupported_llm_response():
    def fake_llm(instruction):
        return {"preference": "make_everyone_fly"}

    with pytest.raises(ValueError):
        interpret_with_llm(
            "Make everyone fly",
            llm_call=fake_llm
        )


# Check that incomplete LLM responses are rejected
def test_missing_preference():
    invalid_responses = [
        {"message": "Done"},
        {},
        {"preference": None},
        None,
        [],
        "preserve_center",
        123
    ]

    for response in invalid_responses:

        def fake_llm(instruction):
            return response

        with pytest.raises(ValueError):
            interpret_with_llm(
                "Keep the center dancers in place",
                llm_call=fake_llm
            )



# Check that empty instructions are rejected
def test_empty_instruction():
    def fake_llm(instruction):
        return {"preference": "minimize_changes"}

    with pytest.raises(ValueError):
        interpret_with_llm("", llm_call=fake_llm)


# Check that API errors are handled
def test_llm_api_failure():
    def fake_llm(instruction):
        raise ConnectionError("API unavailable")

    with pytest.raises(ConnectionError):
        interpret_with_llm(
            "Minimize movement",
            llm_call=fake_llm
        )
