
"""Test how preferences affect symmetry-first formation repair."""

from math import dist

from app.repair import repair


# Create a simple two-row formation
def sample_routine():
    return {
        "stage": {"width": 10, "height": 6},
        "formations": [
            {
                "name": "Two rows",
                "dancers": [
                    {"id": "A", "x": 2, "y": 2},
                    {"id": "B", "x": 4, "y": 2},
                    {"id": "C", "x": 6, "y": 2},
                    {"id": "D", "x": 8, "y": 2},
                    {"id": "E", "x": 2, "y": 4},
                    {"id": "F", "x": 4, "y": 4},
                    {"id": "G", "x": 6, "y": 4},
                    {"id": "H", "x": 8, "y": 4},
                ],
            }
        ],
    }


# Get the repaired dancers
def get_dancers(result):
    return result["routine"]["formations"][0]["dancers"]


# Check that both preferences produce valid formations
def test_both_preferences_are_valid():
    routine = sample_routine()

    for preference in ["minimize_changes", "preserve_center"]:
        result = repair(routine, "G", preference)

        assert result["valid"]
        assert result["errors"] == []


# Check that both preferences preserve clean row spacing
def test_both_preferences_preserve_symmetry():
    routine = sample_routine()

    for preference in ["minimize_changes", "preserve_center"]:
        result = repair(routine, "G", preference)

        # Get the bottom row
        bottom = sorted(
            [
                p for p in get_dancers(result)
                if p["y"] == 4
            ],
            key=lambda p: p["x"]
        )

        # Three dancers remain after G is removed
        assert len(bottom) == 3

        # Check that gaps are equal
        gaps = [
            bottom[i + 1]["x"] - bottom[i]["x"]
            for i in range(len(bottom) - 1)
        ]

        assert max(gaps) - min(gaps) < 0.01

        # Check that the row stays centered
        center = (bottom[0]["x"] + bottom[-1]["x"]) / 2

        assert abs(center - 5.0) < 0.01


# Check that the unaffected row does not move
def test_unaffected_row_stays_unchanged():
    routine = sample_routine()

    original = {
        p["id"]: p
        for p in routine["formations"][0]["dancers"]
    }

    for preference in ["minimize_changes", "preserve_center"]:
        result = repair(routine, "G", preference)

        for p in get_dancers(result):
            if p["id"] in ["A", "B", "C", "D"]:
                assert p["x"] == original[p["id"]]["x"]
                assert p["y"] == original[p["id"]]["y"]


# Check that both preferences minimize unnecessary movement
def test_both_preferences_avoid_unnecessary_movement():
    routine = sample_routine()

    original = {
        p["id"]: p
        for p in routine["formations"][0]["dancers"]
    }

    for preference in ["minimize_changes", "preserve_center"]:
        result = repair(routine, "G", preference)

        # Measure movement of dancers in the unaffected row
        for p in get_dancers(result):
            if p["id"] in ["A", "B", "C", "D"]:
                movement = dist(
                    (p["x"], p["y"]),
                    (
                        original[p["id"]]["x"],
                        original[p["id"]]["y"]
                    )
                )

                assert movement == 0


# Check that the missing dancer is removed
def test_missing_dancer_removed():
    routine = sample_routine()

    for preference in ["minimize_changes", "preserve_center"]:
        result = repair(routine, "G", preference)

        ids = [
            p["id"]
            for p in get_dancers(result)
        ]

        assert "G" not in ids
        assert len(ids) == 7
