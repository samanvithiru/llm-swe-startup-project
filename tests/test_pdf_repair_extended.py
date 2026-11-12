"""Behavior-focused regression tests for PDF formation repair.

These tests complement test_pdf_repair.py; they do not replace existing tests.
"""

import math

import pytest

from app import pdf_repair as pr

STAGE = {"width": 38, "height": 28}


def make(coords):
    return [
        {"id": f"D{i}", "x": float(x), "y": float(y)}
        for i, (x, y) in enumerate(coords)
    ]


def run(coords, missing="D1", preference="minimize_changes", stage=None):
    return pr.repair_pdf_formation(
        {"name": "regression", "dancers": make(coords)},
        missing,
        preference,
        STAGE if stage is None else stage,
    )


def assert_safe(before, after, missing, stage=STAGE):
    assert {p["id"] for p in after} == {p["id"] for p in before} - {missing}
    assert len(after) == len(before) - 1
    assert pr._valid(after, stage)


@pytest.mark.parametrize("points,expected", [
    ([], 2.0),
    ([(2, 2)], 2.0),
    ([(2, 2), (6, 2)], 4.0),
    ([(2, 2), (2.1, 2)], 0.65),
])
def test_nearest_gap_has_safe_default_and_floor(points, expected):
    assert pr._nearest_gap(make(points)) == pytest.approx(expected)


@pytest.mark.parametrize("axis", ["x", "y"])
def test_order_check_rejects_swaps_and_accepts_small_shifts(axis):
    original = make([(3, 3), (7, 7), (11, 11)])
    swapped = [dict(p) for p in original]
    swapped[0][axis], swapped[1][axis] = swapped[1][axis], swapped[0][axis]
    assert not pr._order_preserved(original, swapped, ["D0", "D1"], axis)
    shifted = [dict(p) for p in original]
    shifted[1][axis] += 0.2
    assert pr._order_preserved(original, shifted, ["D0", "D1"], axis)
    assert pr._order_preserved(original, shifted, ["missing", "D1"], axis)


def test_order_check_ignores_tied_original_positions():
    original = make([(3, 3), (3, 6), (7, 9)])
    updated = [dict(p) for p in original]
    updated[0]["x"] = 4
    assert pr._order_preserved(original, updated, ["D0", "D1"], "x")


def test_apply_updates_only_selected_dancers_without_mutation():
    before = make([(2, 3), (6, 3), (10, 3)])
    result = pr._apply(before, {"D1": {"x": 7.5}})
    assert result[1]["x"] == 7.5
    assert result[1]["y"] == 3
    assert result[0] == before[0]
    assert before[1]["x"] == 6


def test_movement_threshold_ignores_tiny_jitter():
    before = make([(2, 3), (6, 3), (10, 3)])
    after = pr._apply(before, {"D0": {"x": 2.1}, "D1": {"x": 6.2}})
    metrics = pr._movement_metrics(before, after)
    assert metrics["moved_dancers"] == 1
    assert metrics["total_displacement"] == pytest.approx(0.3)


@pytest.mark.parametrize("axis,center_mode", [
    ("x", "original"), ("x", "survivors"),
    ("y", "original"), ("y", "survivors"),
    ("diagonal", "original"), ("diagonal", "survivors"),
])
def test_reflow_preserves_survivor_identity(axis, center_mode):
    if axis == "x":
        pts = make([(3, 8), (7, 8), (11, 8), (15, 8), (19, 8)])
    elif axis == "y":
        pts = make([(8, 3), (8, 7), (8, 11), (8, 15), (8, 19)])
    else:
        pts = make([(3, 3), (6, 6), (9, 9), (12, 12), (15, 15)])
    updates = pr._reflow(pts, "D2", axis, center_mode)
    assert set(updates) == {"D0", "D1", "D3", "D4"}
    assert all(math.isfinite(v) for p in updates.values() for v in p.values())
    after = pr._apply([p for p in pts if p["id"] != "D2"], updates)
    assert pr._valid(after, STAGE)


def test_reflow_rejects_insufficient_space_after_shrinking():
    pts = make([(4, 4), (5, 4), (6, 4), (7, 4)])
    assert pr._reflow(pts, "D1", "x", "original", 0.2) == {}


@pytest.mark.parametrize("coords", [
    [(4, 4), (8, 4), (12, 4), (16, 4)],
    [(4, 4), (4, 8), (4, 12), (4, 16)],
    [(4, 4), (8, 8), (12, 12), (16, 16)],
])
def test_linearity_detects_straight_formations(coords):
    assert pr._linearity(make(coords)) == pytest.approx(1.0)


def test_linearity_distinguishes_square_from_line():
    assert pr._linearity(make([(4, 4), (8, 4), (4, 8), (8, 8)])) < 0.7
    assert pr._linearity(make([(4, 4), (8, 8)])) == 0


@pytest.mark.parametrize("axis", ["x", "y"])
def test_symmetry_error_grows_when_mirror_is_broken(axis):
    if axis == "x":
        symmetric = make([(4, 8), (8, 8), (12, 8)])
        asymmetric = make([(4, 8), (8, 8), (14, 8)])
    else:
        symmetric = make([(8, 4), (8, 8), (8, 12)])
        asymmetric = make([(8, 4), (8, 8), (8, 14)])
    assert pr._symmetry(symmetric, axis, 8) == 0
    assert pr._symmetry(asymmetric, axis, 8) > 0


def test_quality_handles_group_that_loses_all_but_one_member():
    old = make([(4, 4), (8, 4), (12, 4)])
    survivors = [old[0], old[2]]
    score, metrics = pr._quality(survivors, survivors, [[old[0]]], "x", "preserve_center", STAGE)
    assert math.isfinite(score)
    assert metrics["row_spacing_error"] == 0
    assert metrics["symmetry_error"] == 0


def test_preserve_center_adds_penalty_for_moving_central_dancer():
    original = make([(15, 14), (19, 14), (23, 14)])
    changed = pr._apply(original, {"D1": {"x": 20}})
    ordinary, _ = pr._quality(changed, original, [original], "x", "minimize_changes", STAGE)
    centered, _ = pr._quality(changed, original, [original], "x", "preserve_center", STAGE)
    assert centered > ordinary


def test_subgroup_detector_returns_none_for_unknown_or_small_formation():
    pts = make([(3, 4), (7, 4), (11, 4), (15, 4)])
    assert pr._repair_separated_group(pts, "unknown", "minimize_changes", STAGE) is None
    assert pr._repair_separated_group(pts, "D1", "minimize_changes", STAGE) is None


def test_subgroup_detector_ignores_single_unbroken_row():
    pts = make([(3, 8), (7, 8), (11, 8), (15, 8), (19, 8)])
    assert pr._repair_separated_group(pts, "D4", "minimize_changes", STAGE) is None


def test_subgroup_detector_rejects_middle_absence():
    pts = make([(2, 7), (6, 7), (10, 7), (19, 7), (23, 7), (27, 7)])
    assert pr._repair_separated_group(pts, "D1", "minimize_changes", STAGE) is None


def test_subgroup_detector_tolerates_small_spacing_variations():
    pts = make([(2, 7), (6, 7), (11, 7), (19, 7), (23, 7), (27, 7)])
    # A small spacing variation should not prevent a safe local repair.
    result = pr._repair_separated_group(pts, "D0", "minimize_changes", STAGE)
    assert result is not None
    assert_safe(pts, result[0], "D0")


def test_subgroup_detector_rebalances_separate_endpoint_group():
    pts = make([(2, 7), (6, 7), (10, 7), (19, 7), (23, 7), (27, 7)])
    result = pr._repair_separated_group(pts, "D0", "minimize_changes", STAGE)
    assert result is not None
    after, info = result
    assert_safe(pts, after, "D0")
    assert info["method"] == "staggered subgroup recentering"
    before_by_id = {p["id"]: p for p in pts}
    after_by_id = {p["id"]: p for p in after}
    assert all(after_by_id[k] == before_by_id[k] for k in ("D3", "D4", "D5"))
    assert after_by_id["D1"]["x"] < after_by_id["D2"]["x"]
    assert after_by_id["D1"]["x"] < before_by_id["D1"]["x"]


def test_subgroup_repair_is_used_by_public_entrypoint():
    coords = [(2, 7), (6, 7), (10, 7), (19, 7), (23, 7), (27, 7)]
    after, info = run(coords, "D0")
    assert_safe(make(coords), after, "D0")
    assert info["method"] == "staggered subgroup recentering"


def test_local_fallback_returns_none_for_unknown_or_too_few_dancers():
    pts = make([(2, 2), (6, 6), (10, 10), (14, 14)])
    assert pr._local_fallback(pts, "unknown", "minimize_changes", STAGE) is None
    assert pr._local_fallback(pts, "D1", "minimize_changes", STAGE) is None


def test_local_fallback_rejects_non_linear_neighborhood():
    pts = make([(4, 4), (8, 4), (4, 8), (8, 8), (12, 12), (15, 3)])
    assert pr._local_fallback(pts, "D1", "minimize_changes", STAGE) is None


@pytest.mark.parametrize("preference", ["minimize_changes", "preserve_center"])
def test_public_repair_is_safe_for_multiple_formations(preference):
    formations = [
        ([(3, 6), (7, 6), (11, 6), (15, 6), (19, 6)], "D2"),
        ([(8, 3), (8, 7), (8, 11), (8, 15), (8, 19)], "D2"),
        ([(4, 4), (7, 7), (10, 10), (13, 13), (16, 16)], "D2"),
        ([(4, 4), (10, 6), (6, 13), (16, 15)], "D1"),
    ]
    for coords, missing in formations:
        before = make(coords)
        after, _ = run(coords, missing, preference)
        assert_safe(before, after, missing)


def test_repair_preserves_additional_dancer_fields():
    pts = make([(3, 8), (7, 8), (11, 8), (15, 8), (19, 8)])
    for p in pts:
        p["label"] = "performer"
    after, _ = pr.repair_pdf_formation({"dancers": pts}, "D1", "minimize_changes", STAGE)
    assert all(p["label"] == "performer" for p in after)


def test_very_narrow_stage_does_not_produce_invalid_repair():
    coords = [(1, 4), (3, 4), (5, 4), (7, 4), (9, 4)]
    stage = {"width": 9, "height": 10}
    before = make(coords)
    after, _ = run(coords, "D1", stage=stage)
    assert_safe(before, after, "D1", stage)


@pytest.mark.parametrize("preference", ["minimize_changes", "preserve_center"])
def test_local_diagonal_fallback_repairs_a_separate_diagonal(preference):
    # A missing middle dancer creates a double gap in a diagonal subgroup.
    # Unrelated dancers elsewhere should remain stationary.
    coords = [
        (3, 3), (6, 6), (9, 9), (12, 12), (15, 15),
        (30, 3), (30, 20),
    ]
    before = make(coords)
    result = pr._local_fallback(before, "D2", preference, STAGE)
    assert result is not None
    after, quality = result
    assert_safe(before, after, "D2")
    assert quality["method"] == "local diagonal subgroup rebalancing"
    assert quality["repaired_score"] < quality["baseline_score"]
    assert quality["improvement_percent"] > 0
    old = {p["id"]: p for p in before}
    new = {p["id"]: p for p in after}
    assert new["D5"] == old["D5"]
    assert new["D6"] == old["D6"]


def test_public_repair_uses_local_diagonal_fallback_when_needed():
    coords = [(3, 3), (6, 6), (9, 9), (12, 12), (15, 15), (30, 3), (30, 20)]
    before = make(coords)
    after, quality = run(coords, "D2")
    assert_safe(before, after, "D2")
    assert quality["method"] == "local diagonal subgroup rebalancing"


def test_local_fallback_preserves_diagonal_with_missing_endpoint():
    coords = [(3, 3), (6, 6), (9, 9), (12, 12), (15, 15), (30, 3), (30, 20)]
    assert pr._local_fallback(make(coords), "D0", "minimize_changes", STAGE) is None
