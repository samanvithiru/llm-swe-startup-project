
"""Repair PDF-imported dance formations while preserving their structure."""

from __future__ import annotations

from math import atan2, cos, hypot, sin

import sys


# --------------------------------------------------
# BASIC HELPERS
# --------------------------------------------------

def _distance(a, b):
    return hypot(a["x"] - b["x"], a["y"] - b["y"])


def _median(values):
    values = sorted(values)

    if not values:
        return 0.0

    n = len(values)
    return (values[(n - 1) // 2] + values[n // 2]) / 2


def _nearest_gap(points):
    if len(points) < 2:
        return 2.0

    distances = [
        min(_distance(p, q) for q in points if q is not p)
        for p in points
    ]

    return max(0.65, _median(distances))


def _cluster(points, coordinate, tolerance):
    groups = []

    for p in sorted(
        points,
        key=lambda q: (q[coordinate], str(q["id"]))
    ):
        choices = [
            (
                abs(
                    p[coordinate]
                    - sum(q[coordinate] for q in group) / len(group)
                ),
                i
            )
            for i, group in enumerate(groups)
        ]

        if choices and min(choices)[0] <= tolerance:
            groups[min(choices)[1]].append(p)
        else:
            groups.append([p])

    return groups


def _valid(points, stage):
    for p in points:
        if not (
            0 <= p["x"] <= stage["width"]
            and 0 <= p["y"] <= stage["height"]
        ):
            return False

    for i, a in enumerate(points):
        for b in points[i + 1:]:
            if _distance(a, b) < 0.6 - 1e-6:
                return False

    return True


def _apply(original, updates):
    return [
        {**p, **updates.get(p["id"], {})}
        for p in original
    ]


def _movement_metrics(original, candidate):
    old = {p["id"]: p for p in original}

    distances = [
        _distance(p, old[p["id"]])
        for p in candidate
    ]

    return {
        "moved_dancers": sum(d > 0.15 for d in distances),
        "total_displacement": round(sum(distances), 4)
    }


def _order_preserved(original, candidate, ids, axis):
    before = {p["id"]: p for p in original}
    after = {p["id"]: p for p in candidate}

    ids = [
        dancer_id for dancer_id in ids
        if dancer_id in before and dancer_id in after
    ]

    for i, first in enumerate(ids):
        for second in ids[i + 1:]:
            old_diff = (
                before[first][axis] - before[second][axis]
            )
            new_diff = (
                after[first][axis] - after[second][axis]
            )

            if abs(old_diff) > 0.15:
                if old_diff * new_diff <= 0:
                    return False

    return True


# --------------------------------------------------
# GEOMETRY HELPERS
# --------------------------------------------------

def _direction(group):
    cx = sum(p["x"] for p in group) / len(group)
    cy = sum(p["y"] for p in group) / len(group)

    xx = sum((p["x"] - cx) ** 2 for p in group)
    yy = sum((p["y"] - cy) ** 2 for p in group)

    xy = sum(
        (p["x"] - cx) * (p["y"] - cy)
        for p in group
    )

    angle = 0.5 * atan2(2 * xy, xx - yy)

    return cos(angle), sin(angle)


def _linearity(group):
    if len(group) < 3:
        return 0.0

    vx, vy = _direction(group)

    cx = sum(p["x"] for p in group) / len(group)
    cy = sum(p["y"] for p in group) / len(group)

    along = sum(
        ((p["x"] - cx) * vx + (p["y"] - cy) * vy) ** 2
        for p in group
    )

    across = sum(
        (-(p["x"] - cx) * vy + (p["y"] - cy) * vx) ** 2
        for p in group
    )

    return along / max(along + across, 1e-9)


def _reflow(group, missing, axis, center_mode, width_factor=1.0):
    survivors = [
        p for p in group
        if p["id"] != missing
    ]

    if len(survivors) < 2:
        return {}

    if axis == "x":
        vx, vy = 1.0, 0.0
    elif axis == "y":
        vx, vy = 0.0, 1.0
    else:
        vx, vy = _direction(group)

    cx = sum(p["x"] for p in group) / len(group)
    cy = sum(p["y"] for p in group) / len(group)

    def project(p):
        return (
            (p["x"] - cx) * vx
            + (p["y"] - cy) * vy
        )

    ordered = sorted(
        survivors,
        key=lambda p: (project(p), str(p["id"]))
    )

    positions = sorted(project(p) for p in group)

    span = (
        positions[-1] - positions[0]
    ) * width_factor

    if span < 0.6 * (len(ordered) - 1):
        return {}

    if center_mode == "original":
        center = (positions[0] + positions[-1]) / 2
    else:
        center = _median([
            project(p) for p in survivors
        ])

    start = center - span / 2
    updates = {}

    for i, p in enumerate(ordered):
        desired = start + i * span / (len(ordered) - 1)
        change = desired - project(p)

        updates[p["id"]] = {
            "x": round(p["x"] + change * vx, 4),
            "y": round(p["y"] + change * vy, 4)
        }

    return updates


# --------------------------------------------------
# QUALITY SCORING
# --------------------------------------------------

def _symmetry(group, axis, center):
    if not group:
        return 0.0

    total = 0.0

    for p in group:
        if axis == "x":
            rx, ry = 2 * center - p["x"], p["y"]
        else:
            rx, ry = p["x"], 2 * center - p["y"]

        total += min(
            hypot(q["x"] - rx, q["y"] - ry)
            for q in group
        )

    return total / len(group)


def _quality(points, original, groups, axis, preference, stage):
    by_id = {p["id"]: p for p in points}
    old = {p["id"]: p for p in original}

    metrics = _movement_metrics(original, points)

    uneven = 0.0
    mirror = 0.0

    for group in groups:
        surviving = [
            by_id[p["id"]]
            for p in group
            if p["id"] in by_id
        ]

        if len(surviving) < 2:
            continue

        center = (
            min(p[axis] for p in group)
            + max(p[axis] for p in group)
        ) / 2

        ordered = sorted(
            surviving,
            key=lambda p: p[axis]
        )

        gaps = [
            b[axis] - a[axis]
            for a, b in zip(ordered, ordered[1:])
        ]

        average = sum(gaps) / len(gaps)

        uneven += sum(
            (g - average) ** 2 for g in gaps
        ) / len(gaps)

        mirror += _symmetry(surviving, axis, center)

    center_x = stage["width"] / 2
    center_y = stage["height"] / 2

    scale = max(
        min(stage["width"], stage["height"]) / 3,
        0.6
    )

    center_movement = 0.0

    for p in points:
        previous = old[p["id"]]

        distance_to_center = hypot(
            previous["x"] - center_x,
            previous["y"] - center_y
        )

        centrality = 1 / (
            1 + (distance_to_center / scale) ** 2
        )

        center_movement += (
            _distance(p, previous) * centrality
        )

    score = (
        5 * uneven
        + 2 * mirror
        + 0.3 * metrics["moved_dancers"]
        + 0.15 * metrics["total_displacement"]
    )

    if preference == "preserve_center":
        score += 1.5 * center_movement

    return score, {
        "symmetry_error": round(mirror, 4),
        "row_spacing_error": round(uneven, 4),
        **metrics,
        "center_displacement": round(center_movement, 4),
        "spacing_penalty": 0.0
    }


# --------------------------------------------------
# STAGGERED SUBGROUP DETECTION
# --------------------------------------------------

def _repair_separated_group(original_all, missing, preference, stage):
    """
    Detect a small, separated horizontal subgroup.

    Allows slight vertical staggering between dancers.
    Preserves left-to-right order and moves only the subgroup.
    """
    absent = next(
        (p for p in original_all if p["id"] == missing),
        None
    )

    if absent is None or len(original_all) < 5:
        return None

    survivors = [
        dict(p) for p in original_all
        if p["id"] != missing
    ]

    gap = _nearest_gap(original_all)

    # Allow staggered rows rather than requiring identical y values.
    row_tolerance = max(0.35, min(0.65, gap * 0.6))

    rows = _cluster(
        original_all,
        "y",
        row_tolerance
    )

    affected_row = next(
        (row for row in rows if absent in row),
        None
    )

    if affected_row is None or len(affected_row) < 3:
        return None

    ordered = sorted(
        affected_row,
        key=lambda p: (p["x"], str(p["id"]))
    )

    gaps = [
        b["x"] - a["x"]
        for a, b in zip(ordered, ordered[1:])
        if b["x"] - a["x"] > 0.2
    ]

    if not gaps:
        return None

    # Use the lower half of the gaps to estimate local spacing.
    smaller = sorted(gaps)[:max(1, (len(gaps) + 1) // 2)]
    typical_gap = _median(smaller)

    if typical_gap < 0.6:
        return None

    # Separate groups at noticeably larger horizontal gaps.
    segments = []
    current = [ordered[0]]

    for previous, person in zip(ordered, ordered[1:]):
        distance = person["x"] - previous["x"]

        if distance > 1.5 * typical_gap:
            segments.append(current)
            current = []

        current.append(person)

    segments.append(current)

    affected = next(
        (segment for segment in segments if absent in segment),
        None
    )

    if affected is None or not 3 <= len(affected) <= 5:
        return None

    # Require evidence that this is a separate subgroup.
    if len(segments) < 2:
        return None

    affected = sorted(
        affected,
        key=lambda p: (p["x"], str(p["id"]))
    )

    original_gaps = [
        b["x"] - a["x"]
        for a, b in zip(affected, affected[1:])
    ]

    spacing = _median(original_gaps)

    if spacing < 0.6:
        return None

    if any(
        abs(g - spacing) > 0.35 * spacing
        for g in original_gaps
    ):
        return None

    # Only recenter a group when the missing dancer was at an end.
    if absent["id"] not in (
        affected[0]["id"],
        affected[-1]["id"]
    ):
        return None

    remaining = [
        p for p in affected
        if p["id"] != missing
    ]

    if len(remaining) < 2:
        return None

    original_center = (
        affected[0]["x"] + affected[-1]["x"]
    ) / 2

    remaining_center = (
        remaining[0]["x"] + remaining[-1]["x"]
    ) / 2

    shift = original_center - remaining_center

    if abs(shift) < 0.05:
        return None

    if abs(shift) > 0.6 * spacing:
        return None

    updates = {
        p["id"]: {
            "x": round(p["x"] + shift, 4),
            "y": p["y"]
        }
        for p in remaining
    }

    candidate = _apply(survivors, updates)

    if not _valid(candidate, stage):
        return None

    if not _order_preserved(
        survivors,
        candidate,
        list(updates),
        "x"
    ):
        return None

    print(
        "DEBUG: SUBGROUP MEMBERS =",
        [p["id"] for p in affected],
        flush=True,
        file=sys.stderr,
    )

    print(
        "DEBUG: SUBGROUP SHIFT =",
        round(shift, 4),
        flush=True,
        file=sys.stderr,
    )

    return candidate, {
        "method": "staggered subgroup recentering",
        "candidates_evaluated": 1,
        "repaired": _movement_metrics(survivors, candidate)
    }


# --------------------------------------------------
# LOCAL DIAGONAL FALLBACK
# --------------------------------------------------

def _local_fallback(original_all, missing, preference, stage):
    absent = next(
        (p for p in original_all if p["id"] == missing),
        None
    )

    survivors = [
        dict(p) for p in original_all
        if p["id"] != missing
    ]

    if absent is None or len(original_all) < 5:
        return None

    gap = _nearest_gap(original_all)

    nearby = sorted(
        original_all,
        key=lambda p: (_distance(p, absent), str(p["id"]))
    )

    candidates = []

    for count in range(4, min(7, len(nearby)) + 1):
        group = nearby[:count]

        if max(
            _distance(p, absent) for p in group
        ) > 3.8 * gap:
            continue

        if _linearity(group) < 0.975:
            continue

        vx, vy = _direction(group)

        cx = sum(p["x"] for p in group) / len(group)
        cy = sum(p["y"] for p in group) / len(group)

        def projection(p):
            return (
                (p["x"] - cx) * vx
                + (p["y"] - cy) * vy
            )

        ordered = sorted(group, key=projection)

        lo = projection(ordered[0])
        hi = projection(ordered[-1])

        extension = any(
            abs(
                -(p["x"] - cx) * vy
                + (p["y"] - cy) * vx
            ) < 0.22 * gap
            and lo - 1.5 * gap <= projection(p) <= hi + 1.5 * gap
            for p in original_all
            if p not in group
        )

        if extension:
            continue

        distances = [
            projection(b) - projection(a)
            for a, b in zip(ordered, ordered[1:])
        ]

        if not distances or min(distances) < 0.6:
            continue

        if max(distances) > 1.7 * min(distances):
            continue

        if absent["id"] in (
            ordered[0]["id"],
            ordered[-1]["id"]
        ):
            continue

        old_survivors = [
            p for p in group
            if p["id"] != missing
        ]

        def gap_variance(points):
            vals = sorted(projection(p) for p in points)

            gaps = [
                b - a for a, b in zip(vals, vals[1:])
            ]

            avg = sum(gaps) / len(gaps)

            return sum(
                (d - avg) ** 2 for d in gaps
            ) / len(gaps)

        before = gap_variance(old_survivors)

        if before < 0.15 * gap * gap:
            continue

        for factor in (1.0, 0.9, 0.8):
            updates = _reflow(
                group,
                missing,
                "diagonal",
                "original",
                factor
            )

            if not updates:
                continue

            candidate = _apply(survivors, updates)

            if not _valid(candidate, stage):
                continue

            new_group = [
                p for p in candidate
                if p["id"] in updates
            ]

            after = gap_variance(new_group)
            metrics = _movement_metrics(survivors, candidate)

            movement = metrics["total_displacement"]

            cost = (
                0.12 if preference == "preserve_center"
                else 0.06
            ) * gap * movement

            improvement = before - after - cost

            if improvement > 0.1 * gap * gap:
                candidates.append((
                    improvement,
                    -movement,
                    candidate,
                    before,
                    after
                ))

    if not candidates:
        return None

    best = max(
        candidates,
        key=lambda item: (item[0], item[1])
    )

    _, _, candidate, before, after = best

    return candidate, {
        "method": "local diagonal subgroup rebalancing",
        "candidates_evaluated": len(candidates),
        "baseline_score": round(before, 4),
        "repaired_score": round(after, 4),
        "improvement_percent": round(
            100 * (before - after) / max(before, 1e-9),
            2
        ),
        "baseline": {
            "row_spacing_error": round(before, 4)
        },
        "repaired": {
            "row_spacing_error": round(after, 4),
            **_movement_metrics(survivors, candidate)
        }
    }


# --------------------------------------------------
# MAIN REPAIR FUNCTION
# --------------------------------------------------

def repair_pdf_formation(formation, missing, preference, stage):
    """Repair PDF formations while preserving dancer order."""

    original_all = formation["dancers"]

    original = [
        dict(p) for p in original_all
        if p["id"] != missing
    ]

    absent = next(
        (p for p in original_all if p["id"] == missing),
        None
    )

    if absent is None or not original:
        return original, {}

    print(
        "DEBUG: REPAIRING FORMATION =",
        formation.get("name", formation.get("source_page", "unknown")),
        flush=True,
        file=sys.stderr,
    )

    # First try repairing a separated, staggered subgroup.
    subgroup_repair = _repair_separated_group(
        original_all,
        missing,
        preference,
        stage
    )

    print(
        "DEBUG: SUBGROUP FOUND =",
        subgroup_repair is not None,
        flush=True,
        file=sys.stderr,
    )

    if subgroup_repair is not None:
        return subgroup_repair

    gap = _nearest_gap(original_all)
    tolerance = max(0.3, min(1.25, gap * 0.27))

    options = []

    for axis, group_key in [
        ("x", "y"),
        ("y", "x")
    ]:
        groups = _cluster(
            original_all,
            group_key,
            tolerance
        )

        affected = next(
            (g for g in groups if absent in g),
            None
        )

        if affected is None or len(affected) < 3:
            continue

        spread = (
            max(p[axis] for p in affected)
            - min(p[axis] for p in affected)
        )

        transverse = (
            max(p[group_key] for p in affected)
            - min(p[group_key] for p in affected)
        )

        if spread < max(1.0, 2 * transverse):
            continue

        for width_factor in (1.0, 0.9, 0.8):
            for center_mode in ("original", "survivors"):
                updates = _reflow(
                    affected,
                    missing,
                    axis,
                    center_mode,
                    width_factor
                )

                if updates:
                    options.append((
                        axis,
                        groups,
                        affected,
                        updates,
                        f"{group_key}-aligned rebalancing"
                    ))

    if (
        len(original_all) >= 4
        and _linearity(original_all) >= 0.97
    ):
        for width_factor in (1.0, 0.9):
            updates = _reflow(
                original_all,
                missing,
                "diagonal",
                "original",
                width_factor
            )

            if updates:
                options.append((
                    "diagonal",
                    [original_all],
                    original_all,
                    updates,
                    "diagonal rebalancing"
                ))

    ranked = []

    for axis, groups, affected, updates, label in options:
        candidate = _apply(original, updates)

        if not _valid(candidate, stage):
            continue

        affected_ids = [
            p["id"] for p in affected
            if p["id"] != missing
        ]

        # Never reverse the order of dancers in a row or column.
        if axis in ("x", "y"):
            if not _order_preserved(
                original,
                candidate,
                affected_ids,
                axis
            ):
                continue

        metrics = _movement_metrics(original, candidate)

        # Reject large changes to a single formation.
        # Localized repairs should normally move only a few dancers.
        if metrics["moved_dancers"] > max(
            2, len(affected_ids) - 1
        ):
            continue

        if metrics["total_displacement"] > (
            1.5 * gap * max(1, metrics["moved_dancers"])
        ):
            continue

        score_axis = "x" if axis == "diagonal" else axis

        score, after = _quality(
            candidate,
            original,
            groups,
            score_axis,
            preference,
            stage
        )

        baseline, before = _quality(
            original,
            original,
            groups,
            score_axis,
            preference,
            stage
        )

        improvement = baseline - score

        if improvement <= 0.001:
            continue

        ranked.append((
            score - baseline,
            metrics["moved_dancers"],
            metrics["total_displacement"],
            label,
            candidate,
            baseline,
            score,
            before,
            after
        ))

    if not ranked:
        fallback = _local_fallback(
            original_all,
            missing,
            preference,
            stage
        )

        if fallback is not None:
            print(
                "DEBUG: USING LOCAL FALLBACK",
                flush=True,
                file=sys.stderr,
            )
            return fallback

        print(
            "DEBUG: PRESERVING ORIGINAL POSITIONS",
            flush=True,
            file=sys.stderr,
        )

        return original, {
            "method": "preserve irregular formation",
            "candidates_evaluated": len(options),
            "repaired": {
                "moved_dancers": 0,
                "total_displacement": 0.0
            }
        }

    ranked.sort(
        key=lambda r: (r[0], r[1], r[2])
    )

    (
        _, _, _, label,
        best, baseline, score,
        before, after
    ) = ranked[0]

    print(
        "DEBUG: SELECTED METHOD =",
        label,
        flush=True,
        file=sys.stderr,
    )

    return best, {
        "method": label,
        "candidates_evaluated": len(options),
        "baseline_score": round(baseline, 4),
        "repaired_score": round(score, 4),
        "improvement_percent": round(
            100 * (baseline - score) / max(baseline, 1e-9),
            2
        ),
        "baseline": before,
        "repaired": after
    }
