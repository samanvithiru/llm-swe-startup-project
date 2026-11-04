
import pytest

from app.openai_adapter import parse_llm_preference


# Check a valid AI response
def test_valid_preference():
    response = '{"preference": "preserve_center"}'

    result = parse_llm_preference(response)

    assert result == {"preference": "preserve_center"}


# Check the other supported preference
def test_minimize_changes():
    response = '{"preference": "minimize_changes"}'

    result = parse_llm_preference(response)

    assert result == {"preference": "minimize_changes"}


# Check that invalid JSON is rejected
def test_invalid_json():
    with pytest.raises(ValueError):
        parse_llm_preference("This is not JSON")


# Check that unsupported preferences are rejected
def test_unsupported_preference():
    response = '{"preference": "make_everyone_fly"}'

    with pytest.raises(ValueError):
        parse_llm_preference(response)


# Check that missing preferences are rejected
def test_missing_preference():
    response = '{"message": "Done"}'

    with pytest.raises(ValueError):
        parse_llm_preference(response)
