
"""RED tests for the separate advanced AI repair endpoint."""

from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

import app.server as server


client = TestClient(server.app)


def source_routine():
    return {
        "stage": {"width": 12, "height": 8},
        "formations": [{
            "name": "Line",
            "dancers": [
                {"id": "A", "x": 2, "y": 4},
                {"id": "B", "x": 4, "y": 4},
                {"id": "C", "x": 6, "y": 4},
                {"id": "D", "x": 8, "y": 4},
            ],
        }],
    }


def test_advanced_ai_route_passes_structured_requirements_to_optimizer(monkeypatch):
    source = source_routine()
    untouched = deepcopy(source)

    desired = {
        "primary_priority": "symmetry",
        "secondary_priorities": ["minimize_dancers_moved"],
        "constraints": {"max_dancers_moved": 3},
    }

    calls = []

    def fake_interpret(instruction):
        calls.append(("interpret", instruction))
        return desired

    def fake_repair(routine, missing, requirements):
        calls.append(("repair", missing, deepcopy(requirements)))

        result = deepcopy(routine)

        for formation in result["formations"]:
            formation["dancers"] = [
                p for p in formation["dancers"]
                if p["id"] != missing
            ]

        return {
            "routine": result,
            "valid": True,
            "errors": [],
            "changed_assignments": 0,
            "total_displacement": 0.0,
        }

    monkeypatch.setattr(
        server,
        "get_ai_requirements",
        fake_interpret,
        raising=False
    )

    monkeypatch.setattr(
        server,
        "repair_with_requirements",
        fake_repair,
        raising=False
    )

    response = client.post(
        "/api/repair-ai",
        json={
            "routine": source,
            "missing": "A",
            "instruction": "Prioritize symmetry, but move at most three dancers.",
        }
    )

    assert response.status_code == 200, response.text

    body = response.json()

    assert body["requirements"] == desired
    assert body["valid"] is True
    assert body["errors"] == []

    assert [
        p["id"]
        for p in body["routine"]["formations"][0]["dancers"]
    ] == ["B", "C", "D"]

    assert calls == [
        (
            "interpret",
            "Prioritize symmetry, but move at most three dancers."
        ),
        ("repair", "A", desired),
    ]

    assert source == untouched


@pytest.mark.parametrize("instruction", ["", "   "])
def test_advanced_ai_route_rejects_empty_instructions(instruction):
    response = client.post(
        "/api/repair-ai",
        json={
            "routine": source_routine(),
            "missing": "A",
            "instruction": instruction,
        }
    )

    assert response.status_code == 400


def test_advanced_ai_route_rejects_unsupported_requirements(monkeypatch):
    def reject(instruction):
        raise ValueError("Unsupported AI requirement")

    monkeypatch.setattr(
        server,
        "get_ai_requirements",
        reject,
        raising=False
    )

    response = client.post(
        "/api/repair-ai",
        json={
            "routine": source_routine(),
            "missing": "A",
            "instruction": "Make the dancers fly",
        }
    )

    assert response.status_code == 400
    assert "unsupported" in response.text.lower()


def test_advanced_ai_failure_does_not_break_manual_repairs(monkeypatch):
    def unavailable(instruction):
        raise ConnectionError("Gemini unavailable")

    monkeypatch.setattr(
        server,
        "get_ai_requirements",
        unavailable,
        raising=False
    )

    advanced = client.post(
        "/api/repair-ai",
        json={
            "routine": source_routine(),
            "missing": "A",
            "instruction": "Prioritize symmetry",
        }
    )

    assert advanced.status_code == 503

    for preference in ("minimize_changes", "preserve_center"):
        manual = client.post(
            "/api/repair",
            json={
                "routine": source_routine(),
                "missing": "A",
                "preference": preference,
            }
        )

        assert manual.status_code == 200, manual.text
        assert manual.json()["valid"] is True


def test_different_ai_priorities_affect_real_repair_coordinates(monkeypatch):
    """Verify that instructions influence positions, not just labels."""

    source = source_routine()

    source["formations"][0]["dancers"].append({
        "id": "E",
        "x": 10,
        "y": 4
    })

    def fake_interpret(instruction):
        priority = (
            "symmetry"
            if "symmetry" in instruction
            else "minimize_dancers_moved"
        )

        return {
            "primary_priority": priority,
            "secondary_priorities": [],
            "constraints": {},
        }

    monkeypatch.setattr(
        server,
        "get_ai_requirements",
        fake_interpret,
        raising=False
    )

    results = {}

    for key, instruction in [
        ("fewest", "Move as few dancers as possible"),
        ("symmetry", "Prioritize symmetry"),
    ]:
        response = client.post(
            "/api/repair-ai",
            json={
                "routine": source,
                "missing": "A",
                "instruction": instruction,
            }
        )

        assert response.status_code == 200, response.text

        result = response.json()

        assert result["valid"]
        assert result["errors"] == []

        assert (
            result["requirements"]["primary_priority"]
            == fake_interpret(instruction)["primary_priority"]
        )

        results[key] = (
            result["routine"]["formations"][0]["dancers"]
        )

    old = {
        p["id"]: p
        for p in source["formations"][0]["dancers"]
    }

    def movement_count(dancers):
        return sum(
            abs(p["x"] - old[p["id"]]["x"]) > 1e-6
            or abs(p["y"] - old[p["id"]]["y"]) > 1e-6
            for p in dancers
        )

    def stage_symmetry_error(dancers):
        # Fixed stage centerline is x=6 in this fixture.
        return sum(
            min(
                abs((12 - p["x"]) - q["x"])
                + abs(p["y"] - q["y"])
                for q in dancers
            )
            for p in dancers
        )

    assert movement_count(results["fewest"]) == 0

    assert (
        stage_symmetry_error(results["symmetry"])
        < stage_symmetry_error(results["fewest"])
    )

    assert (
        movement_count(results["symmetry"])
        > movement_count(results["fewest"])
    )
