
"""Deterministic formation repair for a single unavailable dancer."""

from __future__ import annotations

from math import dist, hypot



def validate(
    routine: dict,
    missing: str | None = None,
    min_spacing: float = 0.6
) -> list[str]:
    errors = []
    width = routine["stage"]["width"]
    height = routine["stage"]["height"]

    # Check that every formation has the same dancers
    if routine["formations"]:
        expected_ids = {
            p["id"]
            for p in routine["formations"][0]["dancers"]
        }

        for fi, formation in enumerate(
            routine["formations"][1:], start=2
        ):
            current_ids = {
                p["id"] for p in formation["dancers"]
            }

            missing_ids = expected_ids - current_ids
            extra_ids = current_ids - expected_ids

            if missing_ids:
                errors.append(
                    f"Formation {fi}: missing dancers {sorted(missing_ids)}"
                )

            if extra_ids:
                errors.append(
                    f"Formation {fi}: unexpected dancers {sorted(extra_ids)}"
                )

    # Validate each formation
    for fi, formation in enumerate(routine["formations"]):
        dancers = formation["dancers"]
        ids = [p["id"] for p in dancers]

        # Check duplicate dancers
        if len(ids) != len(set(ids)):
            errors.append(
                f"Formation {fi + 1}: duplicate dancer ID"
            )

        # Check unavailable dancer
        if missing and missing in ids:
            errors.append(
                f"Formation {fi + 1}: unavailable dancer remains"
            )

        # Check stage boundaries
        for p in dancers:
            if not (
                0 <= p["x"] <= width
                and 0 <= p["y"] <= height
            ):
                errors.append(
                    f"Formation {fi + 1}: {p['id']} outside stage"
                )

        # Check dancer spacing with floating-point tolerance
        for i, a in enumerate(dancers):
            for b in dancers[i + 1:]:
                distance = dist(
                    (a["x"], a["y"]),
                    (b["x"], b["y"])
                )

                if distance < min_spacing - 1e-9:
                    errors.append(
                        f"Formation {fi + 1}: "
                        f"{a['id']} and {b['id']} too close"
                    )

    return errors



def is_two_row_formation(formation: dict) -> bool:
    """Detect two evenly spaced horizontal rows."""

    rows = {}

    for p in formation["dancers"]:
        rows.setdefault(p["y"], []).append(p)

    # Require exactly two rows
    if len(rows) != 2:
        return False

    # Require enough dancers in each row
    if any(len(row) < 3 for row in rows.values()):
        return False

    # Check that both rows have consistent spacing
    for row in rows.values():
        positions = sorted(p["x"] for p in row)

        gaps = [
            positions[i + 1] - positions[i]
            for i in range(len(positions) - 1)
        ]

        if max(gaps) - min(gaps) > 0.01:
            return False

    return True


def repair_two_rows(
    formation: dict,
    missing: str
) -> list[dict]:
    """Find a symmetrical row arrangement with minimal movement."""

    # Copy all available dancers
    dancers = [
        dict(p)
        for p in formation["dancers"]
        if p["id"] != missing
    ]

    # Group the original dancers by row
    rows = {}

    for p in formation["dancers"]:
        rows.setdefault(p["y"], []).append(p)

    if len(rows) != 2:
        raise ValueError("Not a two-row formation")

    # Find the original horizontal center
    all_x = [p["x"] for p in formation["dancers"]]
    center_x = (min(all_x) + max(all_x)) / 2

    # Find the affected row
    affected_y = next(
        y for y, row in rows.items()
        if any(p["id"] == missing for p in row)
    )

    # Sort remaining dancers from left to right
    remaining = sorted(
        [p for p in dancers if p["y"] == affected_y],
        key=lambda p: p["x"]
    )

    count = len(remaining)

    if count <= 1:
        return dancers

    # Find original spacing
    original_row = sorted(
        rows[affected_y],
        key=lambda p: p["x"]
    )

    original_gaps = [
        original_row[i + 1]["x"] - original_row[i]["x"]
        for i in range(len(original_row) - 1)
    ]

    original_spacing = sum(original_gaps) / len(original_gaps)

    # Try different spacing values near the original
    spacing_options = [
        original_spacing * factor
        for factor in (
            0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4
        )
    ]

    best_positions = None
    best_score = None

    for spacing in spacing_options:

        # Center the row
        start_x = center_x - (count - 1) * spacing / 2

        positions = [
            round(start_x + i * spacing, 4)
            for i in range(count)
        ]

        # Keep dancers within the original horizontal range
        if (
            positions[0] < min(all_x)
            or positions[-1] > max(all_x)
        ):
            continue

        # Avoid placing dancers too close together
        if spacing < 0.6:
            continue

        # Calculate how many dancers would move
        moved_count = sum(
            abs(p["x"] - x) > 0.00001
            for p, x in zip(remaining, positions)
        )

        # Calculate total movement
        total_movement = sum(
            abs(p["x"] - x)
            for p, x in zip(remaining, positions)
        )

        # Prioritize fewer dancers moving, then less distance
        score = (
            moved_count,
            total_movement
        )

        if best_score is None or score < best_score:
            best_score = score
            best_positions = positions

    # Apply the best symmetrical arrangement
    if best_positions is not None:
        for p, x in zip(remaining, best_positions):
            p["x"] = x

    return dancers





def _levels(formation):
    levels = {}
    for p in formation["dancers"]:
        levels.setdefault(p["y"], []).append(p)
    return sorted(levels.items())


def is_v_formation(formation):
    """Recognize a symmetric five-person V with its tip at the bottom."""
    levels = _levels(formation)
    if len(levels) != 3 or [len(row) for _, row in levels] != [2, 2, 1]:
        return False
    center = levels[-1][1][0]["x"]
    return all(
        abs(sum(p["x"] for p in row) - 2 * center) < 0.01
        for _, row in levels[:-1]
    ) and all(
        min(p["x"] for p in row) < center < max(p["x"] for p in row)
        for _, row in levels[:-1]
    )


def is_diamond_formation(formation):
    """Recognize a diamond with central top and bottom dancers."""
    levels = _levels(formation)
    if len(levels) < 4 or len(levels[0][1]) != 1 or len(levels[-1][1]) != 1:
        return False
    center = levels[0][1][0]["x"]
    if abs(levels[-1][1][0]["x"] - center) > 0.01:
        return False
    return all(
        len(row) == 2 and abs(sum(p["x"] for p in row) - 2 * center) < 0.01
        for _, row in levels[1:-1]
    )


def is_diagonal_formation(formation):
    """Recognize a straight diagonal with originally even spacing."""
    points = sorted(formation["dancers"], key=lambda p: p["x"])
    if len(points) < 4:
        return False
    dx = points[-1]["x"] - points[0]["x"]
    dy = points[-1]["y"] - points[0]["y"]
    if abs(dx) < 0.01 or abs(dy) < 0.01:
        return False
    if any(abs((p["x"]-points[0]["x"])*dy - (p["y"]-points[0]["y"])*dx) > 0.01 for p in points):
        return False
    gaps = [dist((a["x"], a["y"]), (b["x"], b["y"])) for a,b in zip(points,points[1:])]
    return max(gaps) - min(gaps) < 0.01


def repair_v(formation, missing):
    """Preserve the V tip and restore left-right balance."""
    people = [dict(p) for p in formation["dancers"] if p["id"] != missing]
    levels = _levels(formation)
    center = levels[-1][1][0]["x"]
    for y, original_row in levels[:-1]:
        remaining = [p for p in people if p["y"] == y]
        if len(remaining) == 1:
            # A single unpaired arm dancer moves to the centerline.
            remaining[0]["x"] = center
    return people


def repair_diamond(formation, missing):
    """Keep the top/bottom anchors and balance any unpaired level."""
    people = [dict(p) for p in formation["dancers"] if p["id"] != missing]
    center = _levels(formation)[0][1][0]["x"]
    for y, original_row in _levels(formation)[1:-1]:
        remaining = [p for p in people if p["y"] == y]
        if len(remaining) == 1:
            remaining[0]["x"] = center
    return people


def repair_diagonal(formation, missing):
    """Evenly redistribute remaining dancers along the original diagonal."""
    people = [dict(p) for p in formation["dancers"] if p["id"] != missing]
    people.sort(key=lambda p: p["x"])
    if len(people) <= 1:
        return people
    original = sorted(formation["dancers"], key=lambda p: p["x"])
    first, last = original[0], original[-1]
    for i, p in enumerate(people):
        fraction = i / (len(people) - 1)
        p["x"] = round(first["x"] + fraction * (last["x"] - first["x"]), 4)
        p["y"] = round(first["y"] + fraction * (last["y"] - first["y"]), 4)
    return people


def is_staggered_formation(formation):
    """Recognize two offset, evenly spaced rows with unequal counts."""
    levels = _levels(formation)
    if len(levels) != 2 or min(len(row) for _,row in levels) < 3:
        return False
    if len(levels[0][1]) == len(levels[1][1]):
        return False
    for _,row in levels:
        xs = sorted(p["x"] for p in row)
        gaps = [b-a for a,b in zip(xs,xs[1:])]
        if max(gaps)-min(gaps) > 0.01:
            return False
    return True


def repair_staggered(formation, missing):
    """Keep unaffected row fixed and redistribute the affected row evenly."""
    people = [dict(p) for p in formation["dancers"] if p["id"] != missing]
    original_rows = _levels(formation)
    affected_y = next((y for y,row in original_rows if any(p["id"] == missing for p in row)), None)
    if affected_y is None:
        return people
    remaining = sorted((p for p in people if p["y"] == affected_y), key=lambda p:p["x"])
    if len(remaining) < 2:
        return people
    original_row = next(row for y,row in original_rows if y == affected_y)
    center = (min(p["x"] for p in original_row) + max(p["x"] for p in original_row))/2
    span = max(p["x"] for p in original_row)-min(p["x"] for p in original_row)
    spacing = span/(len(remaining)-1)
    for i,p in enumerate(remaining):
        p["x"] = round(center - span/2 + i*spacing, 4)
    return people




def is_three_column_formation(formation: dict) -> bool:
    """Recognize three evenly spaced vertical columns of four dancers."""
    columns = {}
    for dancer in formation["dancers"]:
        columns.setdefault(dancer["x"], []).append(dancer)
    if len(columns) != 3 or any(len(col) != 4 for col in columns.values()):
        return False
    xs = sorted(columns)
    if abs((xs[1] - xs[0]) - (xs[2] - xs[1])) > 0.15:
        return False
    for col in columns.values():
        ys = sorted(p["y"] for p in col)
        gaps = [b - a for a, b in zip(ys, ys[1:])]
        if min(gaps) < 0.6 or max(gaps) - min(gaps) > 0.15:
            return False
    return True


def _column_candidates(formation: dict, missing: str, stage: dict, preference: str = "minimize_changes") -> list[dict]:
    """Generate three clean column layouts and assign dancers by minimum cost.

    Each candidate preserves three vertical columns and their original centers.
    Assignment uses a bitmask dynamic program, avoiding greedy donor choices.
    """
    original = formation["dancers"]
    available = [p for p in original if p["id"] != missing]
    xs = sorted({p["x"] for p in original})
    if len(xs) != 3 or len(available) != 11:
        return []

    columns = {x: sorted((p["y"] for p in original if p["x"] == x)) for x in xs}
    shapes = [("Balanced 4–3–4", (4, 3, 4)),
              ("Keep left column smaller", (3, 4, 4)),
              ("Keep right column smaller", (4, 4, 3))]
    results = []
    for label, counts in shapes:
        slots = []
        for x, count in zip(xs, counts):
            ys = columns[x]
            low, high = ys[0], ys[-1]
            for i in range(count):
                slots.append((x, low + (high-low)*i/(count-1)))

        # Minimum-cost one-to-one matching; modest penalty for switching columns.
        n = len(available)
        dp = {0: (0.0, ())}
        for person in available:
            nxt = {}
            for mask, (score, path) in dp.items():
                for j, (x, y) in enumerate(slots):
                    if mask & (1 << j):
                        continue
                    movement = hypot(person["x"]-x, person["y"]-y)
                    cost = movement + (0.35 if abs(person["x"]-x) > 0.01 else 0)
                    key = mask | (1 << j)
                    candidate = (score + cost, path + (j,))
                    if key not in nxt or candidate[0] < nxt[key][0]:
                        nxt[key] = candidate
            dp = nxt
        _, assignment = dp[(1 << n)-1]
        assigned = []
        for person, j in zip(available, assignment):
            x, y = slots[j]
            assigned.append({**person, "x": round(x, 4), "y": round(y, 4)})
        trial = {"stage": stage, "formations": [{"name": formation["name"], "dancers": assigned}]}
        if validate(trial):
            continue
        movement = sum(hypot(p["x"]-o["x"], p["y"]-o["y"])
                       for p in assigned for o in available if p["id"] == o["id"])
        changed = sum(hypot(p["x"]-o["x"], p["y"]-o["y"]) >= 0.15
                      for p in assigned for o in available if p["id"] == o["id"])
        # Symmetric outside columns get an explicit aesthetic advantage.
        balance_penalty = 0 if counts == (4, 3, 4) else 2.0

        if preference == "preserve_center":
            center_x = stage["width"] / 2
            center_y = stage["height"] / 2
            center_movement = 0.0
            for dancer in assigned:
                original_dancer = next(p for p in available if p["id"] == dancer["id"])
                distance_from_center = hypot(
                    original_dancer["x"] - center_x,
                    original_dancer["y"] - center_y
                )
                dancer_movement = hypot(
                    dancer["x"] - original_dancer["x"],
                    dancer["y"] - original_dancer["y"]
                )
                center_movement += dancer_movement / (1 + distance_from_center)
            score = movement + 0.15 * changed + balance_penalty + 5.0 * center_movement
        else:
            score = movement + 0.15 * changed + balance_penalty
        results.append({"label": label, "dancers": assigned, "score": score})
    return sorted(results, key=lambda item: item["score"])


def repair_three_columns(formation: dict, missing: str, preference: str = "minimize_changes") -> list[dict]:
    """Return the highest-ranked valid column arrangement."""
    xs = [p["x"] for p in formation["dancers"]]
    ys = [p["y"] for p in formation["dancers"]]
    stage = {"width": max(xs)+2, "height": max(ys)+2}
    candidates = _column_candidates(formation, missing, stage, preference)
    if candidates:
        return candidates[0]["dancers"]
    return [dict(p) for p in formation["dancers"] if p["id"] != missing]


def repair_local(
    formation: dict,
    missing: str,
    preference: str,
    stage: dict
) -> list[dict]:
    """Use the original geometric repair for other formations."""

    # Copy dancers except the unavailable dancer
    missing_positions = [
        p for p in formation["dancers"]
        if p["id"] == missing
    ]

    people = [
        dict(p) for p in formation["dancers"]
        if p["id"] != missing
    ]

    if not missing_positions or not people:
        return people

    vacant = missing_positions[0]

    # Calculate distances from the missing dancer
    distances = [
        hypot(
            p["x"] - vacant["x"],
            p["y"] - vacant["y"]
        )
        for p in people
    ]

    nearest = min(distances)

    # Try different movement strengths
    for strength in (0.24, 0.16, 0.10, 0.05, 0.02):

        candidate = [
            dict(p) for p in people
        ]

        for p, d in zip(candidate, distances):

            weight = strength * (
                nearest / max(d, 0.00001)
            )

            # Reduce movement near the stage center
            if preference == "preserve_center":
                center_distance = hypot(
                    p["x"] - stage["width"] / 2,
                    p["y"] - stage["height"] / 2
                )

                weight *= min(
                    1.0,
                    center_distance / 2.0
                )

            p["x"] = round(
                p["x"] + (vacant["x"] - p["x"]) * weight,
                4
            )

            p["y"] = round(
                p["y"] + (vacant["y"] - p["y"]) * weight,
                4
            )

        # Validate the candidate formation
        trial = {
            "stage": stage,
            "formations": [{
                "name": formation["name"],
                "dancers": candidate
            }]
        }

        if not validate(trial):
            return candidate

    return people


def repair(routine: dict, missing: str, preference: str = "minimize_changes") -> dict:
    """Repair each formation using the appropriate repair algorithm."""

    if not any(
        p["id"] == missing
        for f in routine["formations"]
        for p in f["dancers"]
    ):
        raise ValueError(f"Unknown dancer: {missing}")

    if preference not in ("minimize_changes", "preserve_center"):
        raise ValueError("Unsupported preference")

    result = {
        "stage": dict(routine["stage"]),
        "formations": []
    }

    moved = 0
    displacement = 0.0
    symmetry_repairs = 0
    pdf_quality = []

    for formation in routine["formations"]:

        # Use the adaptive optimizer for every PDF-imported formation.
        if "source_page" in formation:
            from .pdf_repair import repair_pdf_formation

            people, quality = repair_pdf_formation(
                formation,
                missing,
                preference,
                result["stage"]
            )

            pdf_quality.append({
                "formation": formation["name"],
                **quality
            })

        else:
            # Keep the existing shape-aware algorithms for manual formations.
            if is_three_column_formation(formation):
                candidate = repair_three_columns(formation, missing, preference)

            elif is_v_formation(formation):
                candidate = repair_v(formation, missing)

            elif is_diamond_formation(formation):
                candidate = repair_diamond(formation, missing)

            elif is_diagonal_formation(formation):
                candidate = repair_diagonal(formation, missing)

            elif is_staggered_formation(formation):
                candidate = repair_staggered(formation, missing)

            elif is_two_row_formation(formation):
                candidate = repair_two_rows(formation, missing)

            else:
                candidate = None

            if candidate is not None:
                trial = {
                    "stage": result["stage"],
                    "formations": [{
                        "name": formation["name"],
                        "dancers": candidate
                    }]
                }

                if not validate(trial):
                    people = candidate
                    symmetry_repairs += 1
                else:
                    people = repair_local(
                        formation,
                        missing,
                        preference,
                        result["stage"]
                    )

            else:
                people = repair_local(
                    formation,
                    missing,
                    preference,
                    result["stage"]
                )

        # Calculate how many dancers moved and their total displacement.
        before = {
            p["id"]: p
            for p in formation["dancers"]
        }

        for p in people:
            delta = dist(
                (p["x"], p["y"]),
                (before[p["id"]]["x"], before[p["id"]]["y"])
            )

            if delta > 0.00001:
                moved += 1
                displacement += delta

        result["formations"].append({
            "name": formation["name"],
            "dancers": people
        })

    # Validate the entire repaired routine.
    errors = validate(result, missing)

    # Preserve alternative layouts for the original three-column demo.
    alternatives = []

    for idx, formation in enumerate(routine["formations"]):

        if "source_page" in formation:
            continue

        if not is_three_column_formation(formation):
            continue

        for option in _column_candidates(
            formation,
            missing,
            result["stage"],
            preference
        ):
            alternate = {
                "stage": dict(result["stage"]),
                "formations": [
                    {
                        "name": f["name"],
                        "dancers": [
                            dict(p) for p in f["dancers"]
                        ]
                    }
                    for f in result["formations"]
                ]
            }

            alternate["formations"][idx]["dancers"] = option["dancers"]

            if validate(alternate, missing):
                continue

            alternatives.append({
                "label": option["label"],
                "routine": alternate,
                "formation_index": idx
            })

        break

    return {
        "routine": result,
        "valid": not errors,
        "errors": errors,
        "alternatives": alternatives,
        "pdf_repair_quality": pdf_quality,
        "changed_assignments": moved,
        "total_displacement": round(displacement, 4),
        "removed_dancer": missing,
        "method": "symmetry-aware formation repair",
        "note": (
            f"Shape-aware repairs: {symmetry_repairs}. "
            "PDF-imported formations use adaptive geometric repair. "
            "Transitions and choreography still require captain review."
        )
    }

# ---------------------------------------------------------------------------
# New advanced AI-specific interface. Legacy repair() remains unchanged.
# ---------------------------------------------------------------------------
def rank_candidates(source, missing, candidates, requirements):
    from .priority_repair import rank_candidates as _rank
    return _rank(source, missing, candidates, requirements)


def repair_with_requirements(source, missing, requirements):
    from .priority_repair import repair_with_requirements as _repair
    return _repair(source, missing, requirements)
