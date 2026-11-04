
"""Tests for advanced FormationRescue choreography repair."""

from copy import deepcopy
from math import dist

import pytest

from app.repair import repair, validate


# Build a routine from a set of dancer positions
def make_routine(positions, name="Formation"):
    return {
        "stage": {"width": 12, "height": 10},
        "formations": [{
            "name": name,
            "dancers": [
                {"id": dancer_id, "x": x, "y": y}
                for dancer_id, x, y in positions
            ],
        }],
    }


# Get the repaired dancer positions
def get_dancers(result, formation_index=0):
    return result["routine"]["formations"][formation_index]["dancers"]


# Find a dancer by ID
def get_dancer(dancers, dancer_id):
    return next(p for p in dancers if p["id"] == dancer_id)


# Check that two positions are mirrored around a centerline
def mirrored(a, b, center_x=6, tolerance=0.01):
    return (
        abs((a["x"] + b["x"]) - 2 * center_x) <= tolerance
        and abs(a["y"] - b["y"]) <= tolerance
    )


# Create a V formation
def v_formation():
    return make_routine([
        ("A", 2, 2),
        ("B", 4, 4),
        ("C", 6, 6),
        ("D", 8, 4),
        ("E", 10, 2),
    ], "V")


# Create a diamond formation
def diamond_formation():
    return make_routine([
        ("A", 6, 1),
        ("B", 4, 3),
        ("C", 8, 3),
        ("D", 2, 5),
        ("E", 10, 5),
        ("F", 4, 7),
        ("G", 8, 7),
        ("H", 6, 9),
    ], "Diamond")


# Create a diagonal formation
def diagonal_formation():
    return make_routine([
        ("A", 2, 2),
        ("B", 4, 3),
        ("C", 6, 4),
        ("D", 8, 5),
        ("E", 10, 6),
    ], "Diagonal")


# Create staggered rows
def staggered_formation():
    return make_routine([
        ("A", 2, 2),
        ("B", 4, 2),
        ("C", 6, 2),
        ("D", 8, 2),
        ("E", 10, 2),
        ("F", 3, 5),
        ("G", 5, 5),
        ("H", 7, 5),
        ("I", 9, 5),
    ], "Staggered Rows")


# Test removing a dancer from a V formation
def test_v_removes_missing_dancer():
    result = repair(v_formation(), "B")

    assert result["valid"]
    assert "B" not in [p["id"] for p in get_dancers(result)]
    assert len(get_dancers(result)) == 4


# Test that the V retains its central point
def test_v_preserves_center_point():
    result = repair(v_formation(), "B")
    dancers = get_dancers(result)

    center = get_dancer(dancers, "C")

    assert center["x"] == pytest.approx(6, abs=0.01)
    assert center["y"] == pytest.approx(6, abs=0.01)


# Test that the V remains mirrored
def test_v_restores_symmetry():
    result = repair(v_formation(), "B")
    dancers = get_dancers(result)

    left = [p for p in dancers if p["x"] < 6 - 0.01]
    right = [p for p in dancers if p["x"] > 6 + 0.01]

    assert len(left) == len(right)

    for a in left:
        assert any(mirrored(a, b) for b in right)


# Test that a diamond remains valid
def test_diamond_is_valid():
    result = repair(diamond_formation(), "B")

    assert result["valid"]
    assert validate(result["routine"], "B") == []


# Test that the diamond retains its centerline
def test_diamond_preserves_centerline():
    result = repair(diamond_formation(), "B")
    dancers = get_dancers(result)

    assert get_dancer(dancers, "A")["x"] == pytest.approx(6, abs=0.01)
    assert get_dancer(dancers, "H")["x"] == pytest.approx(6, abs=0.01)


# Test that a diamond maintains balanced sides
def test_diamond_balances_sides():
    result = repair(diamond_formation(), "B")
    dancers = get_dancers(result)

    left = sum(p["x"] < 6 - 0.01 for p in dancers)
    right = sum(p["x"] > 6 + 0.01 for p in dancers)

    assert abs(left - right) <= 1


# Test that a diagonal remains valid
def test_diagonal_is_valid():
    result = repair(diagonal_formation(), "C")

    assert result["valid"]


# Test that a diagonal remains a straight line
def test_diagonal_preserves_line():
    result = repair(diagonal_formation(), "C")
    dancers = sorted(get_dancers(result), key=lambda p: p["x"])

    start = dancers[0]
    end = dancers[-1]

    dx = end["x"] - start["x"]
    dy = end["y"] - start["y"]

    for p in dancers:
        cross_product = (
            (p["x"] - start["x"]) * dy
            - (p["y"] - start["y"]) * dx
        )

        assert abs(cross_product) < 0.01


# Test that diagonal spacing is consistent
def test_diagonal_has_even_spacing():
    result = repair(diagonal_formation(), "C")
    dancers = sorted(get_dancers(result), key=lambda p: p["x"])

    gaps = [
        dist(
            (dancers[i]["x"], dancers[i]["y"]),
            (dancers[i + 1]["x"], dancers[i + 1]["y"])
        )
        for i in range(len(dancers) - 1)
    ]

    assert max(gaps) - min(gaps) < 0.01


# Test staggered formation validity
def test_staggered_is_valid():
    result = repair(staggered_formation(), "G")

    assert result["valid"]


# Test that staggered rows remain staggered
def test_staggered_preserves_offset():
    result = repair(staggered_formation(), "G")
    dancers = get_dancers(result)

    top = sorted(
        [p for p in dancers if p["id"] in "ABCDE"],
        key=lambda p: p["x"]
    )

    bottom = sorted(
        [p for p in dancers if p["id"] in "FHI"],
        key=lambda p: p["x"]
    )

    assert len(top) == 5
    assert len(bottom) == 3

    # Rows should remain vertically separated
    assert all(p["y"] == pytest.approx(2, abs=0.01) for p in top)
    assert all(p["y"] == pytest.approx(5, abs=0.01) for p in bottom)

    # The bottom row should remain offset from the top row
    assert abs(bottom[0]["x"] - top[0]["x"]) >= 0.5


# Test that staggered rows have even spacing
def test_staggered_has_even_spacing():
    result = repair(staggered_formation(), "G")
    dancers = get_dancers(result)

    bottom = sorted(
        [p for p in dancers if p["id"] in "FHI"],
        key=lambda p: p["x"]
    )

    gaps = [
        bottom[i + 1]["x"] - bottom[i]["x"]
        for i in range(len(bottom) - 1)
    ]

    assert max(gaps) - min(gaps) < 0.01


# Test that the algorithm reports accurate movement
@pytest.mark.parametrize(
    "routine_factory,missing",
    [
        (v_formation, "B"),
        (diamond_formation, "B"),
        (diagonal_formation, "C"),
        (staggered_formation, "G"),
    ],
)
def test_movement_statistics(routine_factory, missing):
    routine = routine_factory()
    result = repair(routine, missing)

    original = {
        p["id"]: p
        for p in routine["formations"][0]["dancers"]
    }

    movement = sum(
        dist(
            (p["x"], p["y"]),
            (
                original[p["id"]]["x"],
                original[p["id"]]["y"]
            )
        )
        for p in get_dancers(result)
    )

    assert result["total_displacement"] == pytest.approx(
        movement, abs=0.001
    )


# Test that original choreography is not modified
@pytest.mark.parametrize(
    "routine_factory,missing",
    [
        (v_formation, "B"),
        (diamond_formation, "B"),
        (diagonal_formation, "C"),
        (staggered_formation, "G"),
    ],
)
def test_original_is_unchanged(routine_factory, missing):
    routine = routine_factory()
    original = deepcopy(routine)

    repair(routine, missing)

    assert routine == original


# Test that repaired dancers remain onstage
@pytest.mark.parametrize(
    "routine_factory,missing",
    [
        (v_formation, "B"),
        (diamond_formation, "B"),
        (diagonal_formation, "C"),
        (staggered_formation, "G"),
    ],
)
def test_dancers_stay_on_stage(routine_factory, missing):
    routine = routine_factory()
    result = repair(routine, missing)

    for p in get_dancers(result):
        assert 0 <= p["x"] <= 12
        assert 0 <= p["y"] <= 10


# Test repairing the same dancer across multiple formations
def test_repairs_entire_routine():
    v = v_formation()["formations"][0]
    diagonal = diagonal_formation()["formations"][0]

    routine = {
        "stage": {"width": 12, "height": 10},
        "formations": [v, diagonal],
    }

    result = repair(routine, "B")

    assert result["valid"]
    assert len(result["routine"]["formations"]) == 2

    for formation in result["routine"]["formations"]:
        ids = [p["id"] for p in formation["dancers"]]
        assert "B" not in ids
        assert len(ids) == 4


# Test that repairs do not introduce excessive transition movement
def test_transition_movement_is_bounded():
    v = v_formation()["formations"][0]
    diagonal = diagonal_formation()["formations"][0]

    routine = {
        "stage": {"width": 12, "height": 10},
        "formations": [v, diagonal],
    }

    result = repair(routine, "B")

    first = {
        p["id"]: p
        for p in get_dancers(result, 0)
    }

    second = {
        p["id"]: p
        for p in get_dancers(result, 1)
    }

    # Check a broad movement limit between formations
    for dancer_id in first:
        movement = dist(
            (first[dancer_id]["x"], first[dancer_id]["y"]),
            (second[dancer_id]["x"], second[dancer_id]["y"])
        )

        assert movement <= 10
