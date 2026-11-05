from app.repair import validate



def test_missing_dancer_in_one_formation():
    from copy import deepcopy

    routine = {
        "stage": {"width": 12, "height": 8},
        "formations": [
            {
                "name": "Formation 1",
                "dancers": [
                    {"id": "A", "x": 2, "y": 2},
                    {"id": "B", "x": 5, "y": 2},
                    {"id": "C", "x": 8, "y": 2},
                ],
            },
            {
                "name": "Formation 2",
                "dancers": [
                    {"id": "A", "x": 2, "y": 5},
                    {"id": "B", "x": 5, "y": 5},
                ],
            },
        ],
    }

    # Case 1: Dancer missing
    errors = validate(routine)

    assert any("missing" in e.lower() for e in errors)

    # Case 2: Unexpected dancer in second formation
    extra_routine = deepcopy(routine)

    extra_routine["formations"][1]["dancers"].append(
        {"id": "D", "x": 10, "y": 5}
    )

    errors = validate(extra_routine)

    assert any("missing" in e.lower() for e in errors)
    assert any("unexpected" in e.lower() for e in errors)

    # Case 3: Valid matching rosters
    valid_routine = deepcopy(routine)

    valid_routine["formations"][1]["dancers"].append(
        {"id": "C", "x": 8, "y": 5}
    )

    assert validate(valid_routine) == []


    errors = validate(routine)

    assert any("missing" in error.lower() for error in errors)