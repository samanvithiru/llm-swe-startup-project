
"""RED tests for ranking formation repairs by captain priorities."""

from copy import deepcopy
import importlib

import pytest

from app.repair import validate


def original_routine():
    return {
        "stage": {"width": 12, "height": 8},
        "formations": [{
            "name": "Center-stage row",
            "dancers": [
                {"id": "A", "x": 2, "y": 4},
                {"id": "B", "x": 4, "y": 4},
                {"id": "C", "x": 6, "y": 4},
                {"id": "D", "x": 8, "y": 4},
                {"id": "E", "x": 10, "y": 4},
            ],
        }],
    }


def candidate(label, x_positions):
    routine = deepcopy(original_routine())

    routine["formations"][0]["dancers"] = [
        {**person, "x": x_positions[person["id"]]}
        for person in routine["formations"][0]["dancers"]
        if person["id"] != "A"
    ]

    return {"label": label, "routine": routine}


def options():
    return [
        candidate(
            "Remove only",
            {"B": 4, "C": 6, "D": 8, "E": 10}
        ),
        candidate(
            "Best stage symmetry",
            {"B": 3, "C": 5, "D": 7, "E": 9}
        ),
        candidate(
            "One small adjustment",
            {"B": 4, "C": 6, "D": 8, "E": 9}
        ),
    ]


def requirements(priority, maximum=None):
    constraints = (
        {} if maximum is None
        else {"max_dancers_moved": maximum}
    )

    return {
        "primary_priority": priority,
        "secondary_priorities": [],
        "constraints": constraints,
    }


def ranked(candidates, config):
    module = importlib.import_module("app.repair")
    fn = getattr(module, "rank_candidates", None)

    assert callable(fn), "Part 1 RED: implement rank_candidates() in app.repair"

    return fn(
        original_routine(),
        "A",
        candidates,
        config
    )


def changed_count(option):
    before = {
        p["id"]: p
        for p in original_routine()["formations"][0]["dancers"]
    }

    return sum(
        abs(p["x"] - before[p["id"]]["x"]) > 1e-6
        or abs(p["y"] - before[p["id"]]["y"]) > 1e-6
        for p in option["routine"]["formations"][0]["dancers"]
    )


def test_fewest_moved_selects_the_remove_only_option():
    result = ranked(
        options(),
        requirements("minimize_dancers_moved")
    )

    assert result[0]["label"] == "Remove only"
    assert changed_count(result[0]) == 0


def test_least_distance_selects_no_unnecessary_travel():
    result = ranked(
        options(),
        requirements("minimize_total_distance")
    )

    assert result[0]["label"] == "Remove only"


def test_symmetry_selects_a_stage_centered_balanced_row():
    result = ranked(
        options(),
        requirements("symmetry")
    )

    assert result[0]["label"] == "Best stage symmetry"
    assert changed_count(result[0]) > 0


def test_center_preservation_favors_unchanged_center_dancer():
    result = ranked(
        options(),
        requirements("preserve_center")
    )

    chosen = {
        p["id"]: p
        for p in result[0]["routine"]["formations"][0]["dancers"]
    }

    assert chosen["C"]["x"] == 6


def test_max_dancers_moved_is_enforced_before_ranking():
    result = ranked(
        options(),
        requirements("symmetry", maximum=1)
    )

    assert result
    assert all(changed_count(option) <= 1 for option in result)

    assert "Best stage symmetry" not in [
        option["label"] for option in result
    ]


def test_invalid_or_outside_stage_candidates_are_never_offered():
    bad = candidate(
        "Outside stage",
        {"B": 13, "C": 6, "D": 8, "E": 10}
    )

    result = ranked(
        [bad, *options()],
        requirements("minimize_dancers_moved")
    )

    assert "Outside stage" not in [
        option["label"] for option in result
    ]

    assert all(
        validate(option["routine"], missing="A") == []
        for option in result
    )


def test_ranking_preserves_original_data_and_candidate_data():
    input_candidates = options()
    snapshot = deepcopy(input_candidates)

    source = original_routine()
    original_snapshot = deepcopy(source)

    module = importlib.import_module("app.repair")
    fn = getattr(module, "rank_candidates", None)

    assert callable(fn), "Part 1 RED: implement rank_candidates() in app.repair"

    fn(
        source,
        "A",
        input_candidates,
        requirements("symmetry")
    )

    assert source == original_snapshot
    assert input_candidates == snapshot
