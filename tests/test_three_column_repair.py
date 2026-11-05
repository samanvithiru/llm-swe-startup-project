
"""Tests for three-column detection, repair, and alternative layouts."""

import copy
import math

import pytest

from app.repair import (
    _column_candidates,
    is_three_column_formation,
    repair,
    repair_three_columns,
    validate,
)


STAGE = {"width": 38, "height": 28, "units": "ft"}


def make_three_columns():
    """Create three evenly spaced columns with four dancers each."""
    dancers = []
    number = 1

    for x in (8, 18, 28):
        for y in (4, 10, 16, 22):
            dancers.append({
                "id": f"D{number}",
                "x": float(x),
                "y": float(y),
            })
            number += 1

    return {
        "name": "Three Columns",
        "dancers": dancers,
    }


def make_routine(formation):
    """Create a routine containing one formation."""
    return {
        "stage": copy.deepcopy(STAGE),
        "formations": [formation],
    }


def test_three_column_detector_recognizes_valid_formation():
    formation = make_three_columns()

    assert is_three_column_formation(formation)


def test_three_column_detector_rejects_uneven_column_spacing():
    formation = make_three_columns()

    for dancer in formation["dancers"]:
        if dancer["x"] == 28:
            dancer["x"] = 30

    assert not is_three_column_formation(formation)


def test_three_column_detector_rejects_uneven_vertical_spacing():
    formation = make_three_columns()

    formation["dancers"][1]["y"] = 11

    assert not is_three_column_formation(formation)


def test_three_column_detector_rejects_too_close_positions():
    formation = make_three_columns()

    formation["dancers"][1]["y"] = 4.3

    assert not is_three_column_formation(formation)


def test_three_column_detector_rejects_wrong_number_of_dancers():
    formation = make_three_columns()

    formation["dancers"].pop()

    assert not is_three_column_formation(formation)


def test_column_candidates_generate_valid_layouts():
    formation = make_three_columns()

    candidates = _column_candidates(
        formation,
        "D2",
        STAGE,
    )

    assert len(candidates) >= 1

    for candidate in candidates:
        dancers = candidate["dancers"]

        assert len(dancers) == 11
        assert "D2" not in {p["id"] for p in dancers}

        trial = make_routine({
            "name": formation["name"],
            "dancers": dancers,
        })

        assert validate(trial) == []


def test_column_candidates_include_balanced_layout():
    formation = make_three_columns()

    candidates = _column_candidates(
        formation,
        "D2",
        STAGE,
    )

    labels = [candidate["label"] for candidate in candidates]

    assert "Balanced 4–3–4" in labels


def test_column_candidates_have_three_columns():
    formation = make_three_columns()

    candidates = _column_candidates(
        formation,
        "D2",
        STAGE,
    )

    for candidate in candidates:
        columns = {}

        for dancer in candidate["dancers"]:
            columns.setdefault(dancer["x"], []).append(dancer)

        assert len(columns) == 3
        assert sum(len(col) for col in columns.values()) == 11


def test_column_candidates_are_sorted_by_score():
    formation = make_three_columns()

    candidates = _column_candidates(
        formation,
        "D2",
        STAGE,
    )

    scores = [candidate["score"] for candidate in candidates]

    assert scores == sorted(scores)


def test_column_candidates_reject_invalid_dancer_count():
    formation = make_three_columns()

    formation["dancers"].pop()

    candidates = _column_candidates(
        formation,
        "D2",
        STAGE,
    )

    assert candidates == []


def test_three_column_repair_removes_missing_dancer():
    formation = make_three_columns()

    repaired = repair_three_columns(formation, "D2")

    assert len(repaired) == 11
    assert "D2" not in {p["id"] for p in repaired}


def test_three_column_repair_preserves_all_other_dancers():
    formation = make_three_columns()

    repaired = repair_three_columns(formation, "D2")

    original_ids = {
        p["id"] for p in formation["dancers"]
    }

    repaired_ids = {
        p["id"] for p in repaired
    }

    assert repaired_ids == original_ids - {"D2"}


def test_three_column_repair_produces_valid_positions():
    formation = make_three_columns()

    repaired = repair_three_columns(formation, "D2")

    trial = make_routine({
        "name": formation["name"],
        "dancers": repaired,
    })

    assert validate(trial) == []


def test_three_column_repair_does_not_mutate_original():
    formation = make_three_columns()
    original = copy.deepcopy(formation)

    repair_three_columns(formation, "D2")

    assert formation == original


def test_full_repair_generates_alternative_layouts():
    routine = make_routine(make_three_columns())

    result = repair(routine, "D2")

    assert result["valid"]
    assert len(result["alternatives"]) >= 1

    for alternative in result["alternatives"]:
        assert "label" in alternative
        assert "routine" in alternative
        assert "formation_index" in alternative

        assert alternative["formation_index"] == 0
        assert validate(alternative["routine"], "D2") == []


def test_full_repair_preserves_stage():
    routine = make_routine(make_three_columns())

    result = repair(routine, "D2")

    assert result["routine"]["stage"] == STAGE


def test_full_repair_tracks_dancer_movements():
    routine = make_routine(make_three_columns())

    result = repair(routine, "D2")

    assert result["changed_assignments"] >= 0
    assert result["total_displacement"] >= 0

    original = {
        p["id"]: p
        for p in routine["formations"][0]["dancers"]
    }

    repaired = result["routine"]["formations"][0]["dancers"]

    actual_moved = sum(
        math.hypot(
            p["x"] - original[p["id"]]["x"],
            p["y"] - original[p["id"]]["y"],
        ) > 0.00001
        for p in repaired
    )

    assert result["changed_assignments"] == actual_moved


def test_full_repair_returns_multiple_valid_alternatives():
    routine = make_routine(make_three_columns())

    result = repair(routine, "D2")

    alternatives = result["alternatives"]

    assert len(alternatives) >= 2

    for alternative in alternatives:
        assert validate(alternative["routine"], "D2") == []


def test_full_repair_does_not_mutate_original():
    routine = make_routine(make_three_columns())
    original = copy.deepcopy(routine)

    repair(routine, "D2")

    assert routine == original
