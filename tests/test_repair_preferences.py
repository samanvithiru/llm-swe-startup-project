
"""Test how different preferences affect formation repair."""

from app.repair import repair


# Create a simple formation for testing
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


# Check that both preferences generate valid repairs
def test_both_preferences_are_valid():
    routine = sample_routine()

    minimize = repair(routine, "G", "minimize_changes")
    preserve = repair(routine, "G", "preserve_center")

    assert minimize["valid"]
    assert preserve["valid"]


# Check that different preferences affect dancer positions
def test_preferences_produce_different_positions():
    routine = sample_routine()

    minimize = repair(routine, "G", "minimize_changes")
    preserve = repair(routine, "G", "preserve_center")

    assert (
        minimize["routine"]["formations"][0]["dancers"]
        != preserve["routine"]["formations"][0]["dancers"]
    )


# Check that center dancers move less with preserve_center
def test_preserve_center_reduces_center_movement():
    routine = sample_routine()

    minimize = repair(routine, "G", "minimize_changes")
    preserve = repair(routine, "G", "preserve_center")

    def get_position(result, dancer_id):
        dancers = result["routine"]["formations"][0]["dancers"]
        dancer = next(p for p in dancers if p["id"] == dancer_id)
        return dancer["x"], dancer["y"]

    # Dancer C is close to the center of the stage
    original = (6, 2)

    min_pos = get_position(minimize, "C")
    preserve_pos = get_position(preserve, "C")

    min_movement = (
        (min_pos[0] - original[0]) ** 2
        + (min_pos[1] - original[1]) ** 2
    ) ** 0.5

    preserve_movement = (
        (preserve_pos[0] - original[0]) ** 2
        + (preserve_pos[1] - original[1]) ** 2
    ) ** 0.5

    assert preserve_movement < min_movement


# Check that the unavailable dancer is removed
def test_missing_dancer_removed():
    routine = sample_routine()

    for preference in ["minimize_changes", "preserve_center"]:
        result = repair(routine, "G", preference)

        ids = [
            p["id"]
            for p in result["routine"]["formations"][0]["dancers"]
        ]

        assert "G" not in ids
