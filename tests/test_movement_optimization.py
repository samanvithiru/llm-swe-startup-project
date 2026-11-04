"""Test that formation repair avoids unnecessary dancer movement."""

from app.repair import repair


def sample_routine():
    dancers = []

    for row in range(2):
        for col in range(6):
            dancers.append({
                "id": f"{row}-{col}",
                "x": 1 + col * 1.4,
                "y": 2 + row * 2
            })

    return {
        "stage": {"width": 10, "height": 6},
        "formations": [{
            "name": "Two rows",
            "dancers": dancers
        }]
    }


def test_repair_preserves_dancer_order():
    routine = sample_routine()
    result = repair(routine, "1-2")

    bottom = sorted(
        [
            p for p in result["routine"]["formations"][0]["dancers"]
            if p["id"].startswith("1-")
        ],
        key=lambda p: p["x"]
    )

    ids = [p["id"] for p in bottom]

    assert ids == ["1-0", "1-1", "1-3", "1-4", "1-5"]


def test_unaffected_dancers_do_not_move():
    routine = sample_routine()
    result = repair(routine, "1-2")

    original = {
        p["id"]: p
        for p in routine["formations"][0]["dancers"]
    }

    for p in result["routine"]["formations"][0]["dancers"]:
        if p["id"].startswith("0-"):
            assert p["x"] == original[p["id"]]["x"]
            assert p["y"] == original[p["id"]]["y"]


# Check that the reported movement matches actual movement
def test_repair_minimizes_total_movement():
    routine = sample_routine()
    result = repair(routine, "1-2")

    assert result["valid"]

    original = {
        p["id"]: p
        for p in routine["formations"][0]["dancers"]
    }

    repaired = result["routine"]["formations"][0]["dancers"]

    total_movement = sum(
        (
            (p["x"] - original[p["id"]]["x"]) ** 2
            + (p["y"] - original[p["id"]]["y"]) ** 2
        ) ** 0.5
        for p in repaired
    )

    assert abs(
        total_movement - result["total_displacement"]
    ) < 0.001

    assert all(
        p["x"] == original[p["id"]]["x"]
        and p["y"] == original[p["id"]]["y"]
        for p in repaired
        if p["id"].startswith("0-")
    )


# Compare the repair against another symmetrical arrangement
def test_repair_compares_symmetrical_spacing():
    routine = sample_routine()
    result = repair(routine, "1-2")

    original = {
        p["id"]: p
        for p in routine["formations"][0]["dancers"]
    }

    repaired = {
        p["id"]: p
        for p in result["routine"]["formations"][0]["dancers"]
    }

    ids = ["1-0", "1-1", "1-3", "1-4", "1-5"]

    # Calculate movement from the current repair
    actual_movement = sum(
        abs(repaired[id]["x"] - original[id]["x"])
        for id in ids
    )

    # Calculate movement for another centered arrangement
    center = 4.5
    alternative_spacing = 1.6

    alternative_x = [
        center + (i - 2) * alternative_spacing
        for i in range(5)
    ]

    alternative_movement = sum(
        abs(x - original[id]["x"])
        for id, x in zip(ids, alternative_x)
    )

    # Current repair should be no worse than this alternative
    assert actual_movement <= alternative_movement + 0.001
