
"""Tests for app.pdf_repair, including symmetry, safety, and fallbacks."""
import math

import pytest

from app import pdf_repair as pr

STAGE = {"width": 38, "height": 28}


def dancers(coords):
    return [{"id": f"D{i}", "x": float(x), "y": float(y)} for i, (x, y) in enumerate(coords)]


def repair(coords, missing="D1", preference="minimize_changes", stage=None):
    return pr.repair_pdf_formation(
        {"name": "F1", "dancers": dancers(coords)},
        missing,
        preference,
        stage or STAGE,
    )


def assert_safe(before, after, missing, stage=STAGE):
    assert len(after) == len(before) - 1
    assert {p["id"] for p in after} == {p["id"] for p in before} - {missing}
    assert pr._valid(after, stage)
    assert len({p["id"] for p in after}) == len(after)


def test_missing_dancer_not_present_does_not_change_formation():
    before = dancers([(4, 5), (8, 5), (12, 5)])
    original = [dict(p) for p in before]

    for preference in ["minimize_changes", "preserve_center"]:
        for missing in ["Nobody", "Unknown", ""]:
            after, quality = pr.repair_pdf_formation(
                {"dancers": before},
                missing,
                preference,
                STAGE
            )

            assert after == original
            assert quality == {}
            assert before == original


def test_removing_only_dancer_returns_empty():
    after, quality = repair([(8, 8)], "D0")
    assert after == []
    assert quality == {}


def test_irregular_formation_is_preserved_when_no_structure_detected():
    coords = [(4, 4), (10, 6), (6, 13), (16, 15)]
    before = dancers(coords)
    after, quality = repair(coords, "D1")

    assert after == [p for p in before if p["id"] != "D1"]
    assert quality["method"] == "preserve irregular formation"
    assert quality["candidates_evaluated"] == 0


def test_horizontal_row_repair_keeps_dancers_in_row_and_is_safe():
    coords = [(4, 8), (8, 8), (12, 8), (16, 8), (20, 8)]
    before = dancers(coords)
    after, quality = repair(coords, "D1")

    assert_safe(before, after, "D1")
    assert all(p["y"] == pytest.approx(8) for p in after)
    assert [p["id"] for p in sorted(after, key=lambda p: p["x"])] == [
        "D0", "D2", "D3", "D4"
    ]
    assert quality["candidates_evaluated"] > 0


def test_vertical_column_repair_keeps_dancers_in_column_and_is_safe():
    coords = [(9, 3), (9, 7), (9, 11), (9, 15), (9, 19)]
    before = dancers(coords)
    after, quality = repair(coords, "D2")

    assert_safe(before, after, "D2")
    assert all(p["x"] == pytest.approx(9) for p in after)
    assert [p["id"] for p in sorted(after, key=lambda p: p["y"])] == [
        "D0", "D1", "D3", "D4"
    ]
    assert quality["candidates_evaluated"] > 0


def test_other_row_is_not_modified_when_repairing_one_row():
    coords = [
        (4, 6), (8, 6), (12, 6), (16, 6), (20, 6),
        (4, 17), (8, 17), (12, 17), (16, 17), (20, 17),
    ]
    before = dancers(coords)
    after, _ = repair(coords, "D1")

    assert_safe(before, after, "D1")
    old = {p["id"]: p for p in before}

    assert all(
        p["x"] == old[p["id"]]["x"]
        and p["y"] == old[p["id"]]["y"]
        for p in after
        if p["id"] in {"D5", "D6", "D7", "D8", "D9"}
    )


def test_diagonal_line_does_not_leave_stage_or_overlap():
    coords = [(4, 4), (7, 7), (10, 10), (13, 13), (16, 16)]
    before = dancers(coords)
    after, quality = repair(coords, "D1")

    assert_safe(before, after, "D1")
    assert quality["candidates_evaluated"] >= 2


def test_repair_does_not_mutate_input():
    coords = [(4, 8), (8, 8), (12, 8), (16, 8), (20, 8)]
    before = dancers(coords)
    snapshot = [dict(p) for p in before]

    pr.repair_pdf_formation(
        {"dancers": before}, "D1", "preserve_center", STAGE
    )

    assert before == snapshot


def test_preserve_center_preference_produces_valid_layout():
    coords = [(4, 8), (8, 8), (12, 8), (16, 8), (20, 8)]
    before = dancers(coords)
    after, _ = repair(coords, "D1", "preserve_center")

    assert_safe(before, after, "D1")


def test_candidate_positions_rejected_if_outside_stage():
    points = dancers([(0, 2), (4, 2), (8, 2)])

    assert not pr._valid(
        [{**points[0], "x": -0.1}, *points[1:]], STAGE
    )
    assert not pr._valid(
        [{**points[0], "y": 29}, *points[1:]], STAGE
    )


def test_overlapping_dancers_are_invalid():
    assert not pr._valid(dancers([(5, 5), (5.2, 5.2)]), STAGE)
    assert pr._valid(dancers([(5, 5), (6, 5)]), STAGE)


def test_clustering_uses_transverse_coordinate():
    pts = dancers([
        (3, 4.0),
        (8, 4.1),
        (3, 15.0),
        (8, 15.1)
    ])

    # Small variations should remain in the same row
    groups = pr._cluster(pts, "y", 0.2)

    assert len(groups) == 2
    assert sorted(len(g) for g in groups) == [2, 2]

    # A strict tolerance should separate the positions
    strict_groups = pr._cluster(pts, "y", 0.01)

    assert len(strict_groups) == 4
    assert all(len(g) == 1 for g in strict_groups)

    # Large tolerance should combine the nearby points
    wide_groups = pr._cluster(pts, "y", 0.5)

    assert sorted(len(g) for g in wide_groups) == [2, 2]


def test_median_even_and_odd():
    assert pr._median([]) == 0
    assert pr._median([7]) == 7
    assert pr._median([9, 1, 5]) == 5
    assert pr._median([1, 3, 7, 9]) == 5


def test_reflow_rejects_groups_with_fewer_than_two_survivors():
    assert pr._reflow(
        dancers([(2, 4), (6, 4)]),
        "D0",
        "x",
        "original",
    ) == {}


def test_reflow_rejects_too_short_span():
    pts = dancers([(4, 4), (4.1, 4), (4.2, 4), (4.3, 4)])

    assert pr._reflow(pts, "D0", "x", "original") == {}


def test_reflow_diagonal_returns_updates_for_all_survivors():
    pts = dancers([(3, 3), (6, 6), (9, 9), (12, 12)])
    updates = pr._reflow(pts, "D1", "diagonal", "original")

    assert set(updates) == {"D0", "D2", "D3"}



def test_symmetry_error_is_zero_for_mirrored_row():
    # Perfect horizontal symmetry
    symmetric = dancers([
        (4, 8),
        (8, 8),
        (12, 8)
    ])

    assert pr._symmetry(
        symmetric, "x", 8
    ) == pytest.approx(0)

    # One dancer shifted creates asymmetry
    asymmetric = dancers([
        (4, 8),
        (8, 8),
        (13, 8)
    ])

    assert pr._symmetry(
        asymmetric, "x", 8
    ) > 0

    # Perfect vertical symmetry
    vertical = dancers([
        (8, 4),
        (8, 8),
        (8, 12)
    ])

    assert pr._symmetry(
        vertical, "y", 8
    ) == pytest.approx(0)

    # An empty formation should not crash
    assert pr._symmetry([], "x", 8) == 0



def test_quality_reports_movement_and_spacing():
    old = dancers([(4, 8), (8, 8), (12, 8)])
    new = [dict(p) for p in old]
    new[1]["x"] = 9

    score, metrics = pr._quality(
        new, old, [old], "x", "minimize_changes", STAGE
    )

    assert math.isfinite(score)
    assert metrics["moved_dancers"] == 1
    assert metrics["total_displacement"] == pytest.approx(1)
    assert metrics["row_spacing_error"] > 0


def test_repair_quality_contains_expected_metadata_when_improved():
    coords = [(4, 8), (8, 8), (12, 8), (16, 8), (20, 8)]
    after, quality = repair(coords, "D1")

    if quality["method"] not in (
        "preserve irregular formation",
        "remove-only baseline (no valid improvement)",
    ):
        assert quality["repaired_score"] < quality["baseline_score"]
        assert quality["repaired"]["moved_dancers"] >= 1
        assert quality["improvement_percent"] > 0
    else:
        pytest.fail(
            "Expected a valid geometric improvement for this simple row"
        )
