"""US-3: tests written before implementing automatic reblocking."""
from copy import deepcopy
from math import dist

from app.repair import repair, validate


def sample_routine():
    return {
        "stage": {"width": 12, "height": 8},
        "formations": [
            {"name": "Line", "dancers": [
                {"id": "A", "x": 2, "y": 2},
                {"id": "B", "x": 4, "y": 2},
                {"id": "C", "x": 6, "y": 2},
                {"id": "D", "x": 8, "y": 2},
            ]},
            {"name": "Diamond", "dancers": [
                {"id": "A", "x": 6, "y": 1},
                {"id": "B", "x": 3, "y": 4},
                {"id": "C", "x": 9, "y": 4},
                {"id": "D", "x": 6, "y": 7},
            ]},
        ],
    }


def test_reblocking_moves_at_least_one_remaining_dancer():
    original = sample_routine()
    result = repair(original, "B")
    before = {
        (f["name"], p["id"]): (p["x"], p["y"])
        for f in original["formations"] for p in f["dancers"]
    }
    moved = sum(
        (p["x"], p["y"]) != before[(f["name"], p["id"])]
        for f in result["routine"]["formations"] for p in f["dancers"]
    )
    assert moved > 0, "A repair must do more than remove the absent dancer"
    assert result["changed_assignments"] == moved


def test_reblocking_reports_actual_total_displacement():
    original = sample_routine()
    result = repair(original, "B")
    before = {
        (f["name"], p["id"]): (p["x"], p["y"])
        for f in original["formations"] for p in f["dancers"]
    }
    actual = sum(
        dist((p["x"], p["y"]), before[(f["name"], p["id"])])
        for f in result["routine"]["formations"] for p in f["dancers"]
    )
    assert "total_displacement" in result
    assert abs(result["total_displacement"] - actual) < 0.001


def test_reblocking_preserves_original_and_constraints():
    original = sample_routine()
    saved = deepcopy(original)
    result = repair(original, "B")
    assert original == saved
    assert result["valid"]
    assert validate(result["routine"], missing="B") == []
    for formation in result["routine"]["formations"]:
        assert {p["id"] for p in formation["dancers"]} == {"A", "C", "D"}
