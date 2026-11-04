
"""Test that repaired formations have clean, symmetrical rows."""

from app.repair import repair


# Create a formation with two rows of six dancers
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


# Check that the repaired row is evenly spaced and centered
def test_repair_creates_symmetrical_rows():
    routine = sample_routine()

    result = repair(routine, "1-2")

    assert result["valid"]

    dancers = result["routine"]["formations"][0]["dancers"]

    # Get dancers in the bottom row
    bottom = sorted(
        [p for p in dancers if p["id"].startswith("1-")],
        key=lambda p: p["x"]
    )

    # Five dancers should remain in the bottom row
    assert len(bottom) == 5

    # Check that spacing is equal
    gaps = [
        bottom[i + 1]["x"] - bottom[i]["x"]
        for i in range(len(bottom) - 1)
    ]

    assert max(gaps) - min(gaps) < 0.01

    # Check that the row is centered
    center = (bottom[0]["x"] + bottom[-1]["x"]) / 2

    assert abs(center - 4.5) < 0.01


# Check that the top row remains unchanged
def test_unaffected_row_stays_in_place():
    routine = sample_routine()

    result = repair(routine, "1-2")

    original = {
        p["id"]: p
        for p in routine["formations"][0]["dancers"]
    }

    repaired = result["routine"]["formations"][0]["dancers"]

    for p in repaired:
        if p["id"].startswith("0-"):
            assert p["x"] == original[p["id"]]["x"]
            assert p["y"] == original[p["id"]]["y"]
