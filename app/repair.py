
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

        # Check dancer spacing
        for i, a in enumerate(dancers):
            for b in dancers[i + 1:]:
                if dist(
                    (a["x"], a["y"]),
                    (b["x"], b["y"])
                ) < min_spacing:
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
    """Recenter the affected row while keeping the other row fixed."""

    # Copy remaining dancers
    dancers = [
        dict(p)
        for p in formation["dancers"]
        if p["id"] != missing
    ]

    # Group original dancers by row
    rows = {}

    for p in formation["dancers"]:
        rows.setdefault(p["y"], []).append(p)

    if len(rows) != 2:
        raise ValueError("Not a two-row formation")

    # Find the formation's horizontal center
    all_x = [
        p["x"]
        for p in formation["dancers"]
    ]

    center_x = (min(all_x) + max(all_x)) / 2

    # Find the original dancer spacing
    original_row = sorted(
        next(iter(rows.values())),
        key=lambda p: p["x"]
    )

    gaps = [
        original_row[i + 1]["x"] - original_row[i]["x"]
        for i in range(len(original_row) - 1)
    ]

    spacing = sum(gaps) / len(gaps)

    # Rebuild only the row containing the missing dancer
    for y, original_dancers in rows.items():

        if not any(
            p["id"] == missing
            for p in original_dancers
        ):
            continue

        remaining = sorted(
            [
                p for p in dancers
                if p["y"] == y
            ],
            key=lambda p: p["x"]
        )

        count = len(remaining)

        # Calculate evenly spaced centered positions
        start_x = center_x - (count - 1) * spacing / 2

        for i, p in enumerate(remaining):
            p["x"] = round(
                start_x + i * spacing, 4
            )

    return dancers


def repair_local(
    formation: dict,
    missing: str,
    preference: str,
    stage: dict
) -> list[dict]:
    """Use the original geometric repair for other formations."""

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

    # Try different adjustment strengths
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

        # Check whether the adjustment is valid
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


def repair(
    routine: dict,
    missing: str,
    preference: str = "minimize_changes"
) -> dict:
    """Repair formations using symmetry when possible."""

    # Check that the missing dancer exists
    if not any(
        p["id"] == missing
        for f in routine["formations"]
        for p in f["dancers"]
    ):
        raise ValueError(
            f"Unknown dancer: {missing}"
        )

    # Check supported preferences
    if preference not in (
        "minimize_changes",
        "preserve_center"
    ):
        raise ValueError(
            "Unsupported preference"
        )

    result = {
        "stage": dict(routine["stage"]),
        "formations": []
    }

    moved = 0
    displacement = 0.0
    symmetry_repairs = 0

    # Repair every formation
    for formation in routine["formations"]:

        # Use symmetrical repair for clean two-row formations
        if is_two_row_formation(formation):
            candidate = repair_two_rows(
                formation,
                missing
            )

            trial = {
                "stage": result["stage"],
                "formations": [{
                    "name": formation["name"],
                    "dancers": candidate
                }]
            }

            # Use the symmetrical result if it is valid
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
            # Use original repair for other formations
            people = repair_local(
                formation,
                missing,
                preference,
                result["stage"]
            )

        # Calculate movement statistics
        before = {
            p["id"]: p
            for p in formation["dancers"]
        }

        for p in people:
            delta = dist(
                (p["x"], p["y"]),
                (
                    before[p["id"]]["x"],
                    before[p["id"]]["y"]
                )
            )

            if delta > 0.00001:
                moved += 1
                displacement += delta

        # Save the repaired formation
        result["formations"].append({
            "name": formation["name"],
            "dancers": people
        })

    # Validate the complete repaired routine
    errors = validate(result, missing)

    return {
        "routine": result,
        "valid": not errors,
        "errors": errors,
        "changed_assignments": moved,
        "total_displacement": round(displacement, 4),
        "removed_dancer": missing,
        "method": "symmetry-aware formation repair",
        "note": (
            f"Symmetrical row repairs: {symmetry_repairs}. "
            "Other formations use local geometric adjustments. "
            "Transitions and choreography still require captain review."
        )
    }
