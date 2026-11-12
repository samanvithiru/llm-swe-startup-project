
"""RED tests for Part 1: Gemini must extract structured captain requirements."""

import json
from types import SimpleNamespace

import pytest

import app.gemini_request as gemini_module
import app.openai_adapter as adapter_module


def parse_requirements(raw):
    parser = getattr(adapter_module, "parse_ai_requirements", None)
    assert callable(parser), "Part 1 RED: implement parse_ai_requirements()"
    return parser(raw)


@pytest.mark.parametrize(
    "primary,secondary",
    [
        ("symmetry", ["minimize_dancers_moved"]),
        ("minimize_dancers_moved", []),
        ("minimize_total_distance", ["symmetry"]),
        ("preserve_center", []),
    ],
)
def test_supported_requirements_are_preserved(primary, secondary):
    payload = {
        "primary_priority": primary,
        "secondary_priorities": secondary,
        "constraints": {},
    }
    assert parse_requirements(json.dumps(payload)) == payload


def test_numeric_limit_is_kept_as_a_hard_constraint():
    payload = {
        "primary_priority": "symmetry",
        "secondary_priorities": ["minimize_dancers_moved"],
        "constraints": {"max_dancers_moved": 3},
    }
    assert parse_requirements(json.dumps(payload)) == payload


@pytest.mark.parametrize(
    "bad_response",
    [
        "not JSON",
        "[]",
        "null",
        "{}",
        '{"primary_priority":"make_everyone_fly","secondary_priorities":[],"constraints":{}}',
        '{"primary_priority":"symmetry","secondary_priorities":["symmetry"],"constraints":{}}',
        '{"primary_priority":"symmetry","secondary_priorities":[],"constraints":{"max_dancers_moved":-1}}',
        '{"primary_priority":"symmetry","secondary_priorities":[],"constraints":{"max_dancers_moved":"three"}}',
        '{"primary_priority":"symmetry","secondary_priorities":[],"constraints":{"unsupported_rule":true}}',
    ],
)
def test_bad_or_unsupported_ai_requirements_are_rejected(bad_response):
    with pytest.raises(ValueError):
        parse_requirements(bad_response)


def test_gemini_sends_the_original_instruction_and_gets_structured_requirements():
    calls = []
    expected = {
        "primary_priority": "symmetry",
        "secondary_priorities": ["minimize_dancers_moved"],
        "constraints": {"max_dancers_moved": 3},
    }

    class FakeModels:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(text=json.dumps(expected))

    getter = getattr(gemini_module, "get_gemini_requirements", None)
    assert callable(getter), "Part 1 RED: implement get_gemini_requirements()"

    instruction = "Prioritize symmetry, but move no more than three dancers."
    result = getter(instruction, client=SimpleNamespace(models=FakeModels()))

    assert result == expected
    assert len(calls) == 1
    assert instruction in str(calls[0]["contents"])

    prompt = str(calls[0]["contents"])
    assert "symmetry" in prompt
    assert "minimize_dancers_moved" in prompt
    assert "minimize_total_distance" in prompt
    assert "max_dancers_moved" in prompt


def test_legacy_gemini_preference_function_still_exists():
    assert callable(gemini_module.get_gemini_preference)
