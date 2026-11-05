
"""Additional tests for FormationRescue's main repair module."""

import copy
import math

import pytest

from app.repair import repair, validate


STAGE = {"width": 38, "height": 28, "units": "ft"}


def make_formation(name, positions):
    """Create a formation from dancer coordinates."""
    return {
        "name": name,
        "dancers": [
            {"id": dancer_id, "x": float(x), "y": float(y)}
            for dancer_id, x, y in positions
        ],
    }


def make_routine(*formations):
    """Create a routine with one or more formations."""
    return {
        "stage": copy.deepcopy(STAGE),
        "formations": list(formations),
    }


def basic_row():
    """Create a simple horizontal formation."""
    return make_formation(
        "Row",
        [
            ("A", 4, 8),
            ("B", 8, 8),
            ("C", 12, 8),
            ("D", 16, 8),
            ("E", 20, 8),
        ],
    )


def basic_column():
    """Create a simple vertical formation."""
    return make_formation(
        "Column",
        [
            ("A", 10, 4),
            ("B", 10, 8),
            ("C", 10, 12),
            ("D", 10, 16),
            ("E", 10, 20),
        ],
    )


def basic_diagonal():
    """Create a diagonal formation."""
    return make_formation(
        "Diagonal",
        [
            ("A", 4, 4),
            ("B", 8, 8),
            ("C", 12, 12),
            ("D", 16, 16),
            ("E", 20, 20),
        ],
    )


def basic_two_rows():
    """Create two horizontal rows."""
    return make_formation(
        "Two Rows",
        [
            ("A", 4, 6),
            ("B", 8, 6),
            ("C", 12, 6),
            ("D", 16, 6),
            ("E", 20, 6),
            ("F", 4, 18),
            ("G", 8, 18),
            ("H", 12, 18),
            ("I", 16, 18),
            ("J", 20, 18),
        ],
    )


def assert_correct_roster(original, repaired, missing):
    """Check that only the missing dancer was removed."""
    old_ids = {
        p["id"]
        for p in original["dancers"]
    }

    new_ids = [
        p["id"]
        for p in repaired["dancers"]
    ]

    assert missing not in new_ids
    assert len(new_ids) == len(set(new_ids))
    assert set(new_ids) == old_ids - {missing}


def assert_safe_positions(routine):
    """Check stage boundaries and dancer spacing."""
    stage = routine["stage"]

    for formation in routine["formations"]:
        dancers = formation["dancers"]

        for dancer in dancers:
            assert 0 <= dancer["x"] <= stage["width"]
            assert 0 <= dancer["y"] <= stage["height"]

        for i, first in enumerate(dancers):
            for second in dancers[i + 1:]:
                distance = math.hypot(
                    first["x"] - second["x"],
                    first["y"] - second["y"],
                )

                assert distance >= 0.6 - 1e-6


# --------------------------------------------------
# Basic repair tests
# --------------------------------------------------

def test_repair_returns_expected_fields():
    routine = make_routine(basic_row())

    result = repair(routine, "B")

    assert isinstance(result, dict)
    assert "routine" in result
    assert "valid" in result
    assert "errors" in result
    assert "alternatives" in result
    assert "changed_assignments" in result
    assert "total_displacement" in result
    assert "removed_dancer" in result
    assert "method" in result


def test_repair_removes_correct_dancer():
    routine = make_routine(basic_row())

    result = repair(routine, "B")

    repaired = result["routine"]["formations"][0]

    assert_correct_roster(
        routine["formations"][0],
        repaired,
        "B",
    )


def test_repair_preserves_formation_name():
    routine = make_routine(basic_row())

    result = repair(routine, "B")

    assert result["routine"]["formations"][0]["name"] == "Row"


def test_repair_preserves_stage_dimensions():
    routine = make_routine(basic_row())

    result = repair(routine, "B")

    assert result["routine"]["stage"] == STAGE


def test_repair_does_not_modify_original_input():
    routine = make_routine(basic_row())
    original = copy.deepcopy(routine)

    repair(routine, "B")

    assert routine == original


def test_repair_preserves_surviving_dancer_ids():
    routine = make_routine(basic_row())

    result = repair(routine, "C")

    repaired = result["routine"]["formations"][0]

    assert_correct_roster(
        routine["formations"][0],
        repaired,
        "C",
    )


# --------------------------------------------------
# Formation structure tests
# --------------------------------------------------

@pytest.mark.parametrize(
    "formation,missing",
    [
        (basic_row, "B"),
        (basic_column, "C"),
        (basic_diagonal, "B"),
        (basic_two_rows, "B"),
    ],
)
def test_different_formation_types_keep_correct_roster(
    formation,
    missing,
):
    routine = make_routine(formation())

    result = repair(routine, missing)

    assert_correct_roster(
        routine["formations"][0],
        result["routine"]["formations"][0],
        missing,
    )


@pytest.mark.parametrize(
    "formation,missing",
    [
        (basic_row, "B"),
        (basic_column, "C"),
        (basic_diagonal, "B"),
        (basic_two_rows, "B"),
    ],
)
def test_different_formation_types_have_safe_positions(
    formation,
    missing,
):
    routine = make_routine(formation())

    result = repair(routine, missing)

    assert_safe_positions(result["routine"])


def test_multiple_formations_are_all_processed():
    routine = make_routine(
        basic_row(),
        basic_column(),
        basic_diagonal(),
    )

    result = repair(routine, "B")

    assert len(result["routine"]["formations"]) == 3

    for old, new in zip(
        routine["formations"],
        result["routine"]["formations"],
    ):
        assert_correct_roster(old, new, "B")


def test_multiple_formations_keep_original_order():
    routine = make_routine(
        basic_row(),
        basic_column(),
        basic_diagonal(),
    )

    result = repair(routine, "B")

    names = [
        f["name"]
        for f in result["routine"]["formations"]
    ]

    assert names == ["Row", "Column", "Diagonal"]


# --------------------------------------------------
# Preference tests
# --------------------------------------------------

@pytest.mark.parametrize(
    "preference",
    [
        "minimize_changes",
        "preserve_center",
    ],
)
def test_supported_preferences_return_results(preference):
    routine = make_routine(basic_row())

    result = repair(routine, "B", preference)

    assert "routine" in result
    assert_correct_roster(
        routine["formations"][0],
        result["routine"]["formations"][0],
        "B",
    )


def test_invalid_preference_raises_error():
    routine = make_routine(basic_row())

    with pytest.raises(ValueError):
        repair(routine, "B", "random_preference")


def test_unknown_dancer_raises_error():
    routine = make_routine(basic_row())

    with pytest.raises(ValueError):
        repair(routine, "NOT_A_DANCER")


# --------------------------------------------------
# Movement metric tests
# --------------------------------------------------

def test_movement_count_is_nonnegative():
    routine = make_routine(basic_row())

    result = repair(routine, "B")

    assert isinstance(result["changed_assignments"], int)
    assert result["changed_assignments"] >= 0


def test_total_displacement_is_nonnegative():
    routine = make_routine(basic_row())

    result = repair(routine, "B")

    assert result["total_displacement"] >= 0


def test_reported_movement_count_matches_actual_positions():
    routine = make_routine(basic_row())

    result = repair(routine, "B")

    before = {
        p["id"]: p
        for p in routine["formations"][0]["dancers"]
    }

    after = result["routine"]["formations"][0]["dancers"]

    actual_moved = sum(
        math.hypot(
            p["x"] - before[p["id"]]["x"],
            p["y"] - before[p["id"]]["y"],
        ) > 0.00001
        for p in after
    )

    assert result["changed_assignments"] == actual_moved


def test_reported_displacement_matches_actual_movement():
    routine = make_routine(basic_row())

    result = repair(routine, "B")

    before = {
        p["id"]: p
        for p in routine["formations"][0]["dancers"]
    }

    after = result["routine"]["formations"][0]["dancers"]

    actual_distance = sum(
        math.hypot(
            p["x"] - before[p["id"]]["x"],
            p["y"] - before[p["id"]]["y"],
        )
        for p in after
    )

    assert result["total_displacement"] == pytest.approx(
        actual_distance,
        abs=0.0001,
    )


# --------------------------------------------------
# Validation tests
# --------------------------------------------------

def test_valid_routine_has_no_validation_errors():
    routine = make_routine(basic_row())

    assert validate(routine) == []


def test_overlapping_dancers_are_rejected():
    formation = make_formation(
        "Overlap",
        [
            ("A", 5, 5),
            ("B", 5.1, 5.1),
            ("C", 12, 12),
        ],
    )

    errors = validate(make_routine(formation))

    assert len(errors) > 0


def test_dancer_outside_stage_is_rejected():
    formation = make_formation(
        "Outside",
        [
            ("A", -2, 5),
            ("B", 8, 8),
            ("C", 12, 12),
        ],
    )

    errors = validate(make_routine(formation))

    assert len(errors) > 0


def test_dancer_above_stage_height_is_rejected():
    formation = make_formation(
        "Outside",
        [
            ("A", 4, 30),
            ("B", 8, 8),
            ("C", 12, 12),
        ],
    )

    errors = validate(make_routine(formation))

    assert len(errors) > 0


def test_duplicate_dancer_ids_are_rejected():
    formation = make_formation(
        "Duplicates",
        [
            ("A", 4, 4),
            ("A", 8, 8),
            ("B", 12, 12),
        ],
    )

    errors = validate(make_routine(formation))

    assert len(errors) > 0


# --------------------------------------------------
# Output consistency tests
# --------------------------------------------------

def test_removed_dancer_metadata_is_correct():
    routine = make_routine(basic_row())

    result = repair(routine, "B")

    assert result["removed_dancer"] == "B"


def test_errors_field_is_a_list():
    routine = make_routine(basic_row())

    result = repair(routine, "B")

    assert isinstance(result["errors"], list)


def test_alternatives_field_is_a_list():
    routine = make_routine(basic_row())

    result = repair(routine, "B")

    assert isinstance(result["alternatives"], list)


def test_repair_is_deterministic():
    routine = make_routine(basic_row())

    first = repair(copy.deepcopy(routine), "B")
    second = repair(copy.deepcopy(routine), "B")

    assert first["routine"] == second["routine"]
    assert first["changed_assignments"] == second["changed_assignments"]
    assert first["total_displacement"] == second["total_displacement"]
