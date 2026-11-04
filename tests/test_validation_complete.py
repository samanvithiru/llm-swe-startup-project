from app.repair import validate


def test_missing_dancer_in_one_formation():
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

    errors = validate(routine)

    assert any("missing" in error.lower() for error in errors)