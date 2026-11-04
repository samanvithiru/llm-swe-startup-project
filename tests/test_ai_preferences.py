import pytest

from app.ai_preferences import interpret_preference


def test_minimize_movement():
    result = interpret_preference("Minimize movement for everyone")
    assert result["preference"] == "minimize_changes"


def test_preserve_center():
    result = interpret_preference("Keep the center dancers in place")
    assert result["preference"] == "preserve_center"


def test_unsupported_instruction():
    with pytest.raises(ValueError):
        interpret_preference("Make everyone do a backflip")


def test_empty_instruction():
    with pytest.raises(ValueError):
        interpret_preference("")
