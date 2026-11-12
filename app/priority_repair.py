"""Advanced AI repair candidate generation and objective-aware ranking.

This module is NEW and is intentionally separate from the legacy repair()
entrypoint. The manual two-option workflow is not modified.

Part 1: one best validated result. Part 2 will expose multiple suggestions.
"""

from copy import deepcopy
from math import hypot, isfinite
from statistics import median

from app.ai_requirements import validate_ai_requirements

MOVEMENT_EPSILON = 1e-5


def _has_correct_roster(source, missing, proposed):
    if not isinstance(proposed, dict) or proposed.get("stage") != source.get("stage"):
        return False
    old_forms = source.get("formations", [])
    new_forms = proposed.get("formations", [])
    if not isinstance(new_forms, list) or len(new_forms) != len(old_forms):
        return False
    for old, new in zip(old_forms, new_forms):
        if new.get("name") != old.get("name"):
            return False
        expected = [p["id"] for p in old["dancers"] if p["id"] != missing]
        actual = [p.get("id") for p in new.get("dancers", [])]
        if len(actual) != len(expected) or len(actual) != len(set(actual)):
            return False
        if set(actual) != set(expected):
            return False
        for p in new["dancers"]:
            if (not isinstance(p.get("x"), (int, float))
                    or not isinstance(p.get("y"), (int, float))
                    or not isfinite(p["x"]) or not isfinite(p["y"])):
                return False
    return True


def _metrics(source, option):
    proposed = option["routine"]
    changed, total, center_movement = 0, 0.0, 0.0
    symmetry, uneven = 0.0, 0.0
    stage = source["stage"]
    cx = stage["width"] / 2
    cy = stage["height"] / 2
    for before_form, after_form in zip(source["formations"], proposed["formations"]):
        old = {p["id"]: p for p in before_form["dancers"]}
        pts = after_form["dancers"]
        for p in pts:
            before = old[p["id"]]
            delta = hypot(p["x"] - before["x"], p["y"] - before["y"])
            total += delta
            if delta > MOVEMENT_EPSILON:
                changed += 1
            distance_to_center = hypot(before["x"] - cx, before["y"] - cy)
            center_movement += delta / (1 + distance_to_center)

        # Symmetry is measured relative to the physical stage's vertical
        # midline. The nearest dancer to each mirrored point contributes the
        # residual error. No imaginary dancers are introduced.
        for p in pts:
            mirror_x = 2 * cx - p["x"]
            symmetry += min(
                (hypot(q["x"] - mirror_x, q["y"] - p["y"]) for q in pts),
                default=0.0,
            )

        # Penalize uneven spacing inside clearly horizontal rows.
        rows = {}
        for p in pts:
            rows.setdefault(round(float(p["y"]), 2), []).append(p["x"])
        for xs in rows.values():
            if len(xs) < 3:
                continue
            sorted_x = sorted(xs)
            gaps = [b - a for a, b in zip(sorted_x, sorted_x[1:])]
            mean = sum(gaps) / len(gaps)
            uneven += sum((g - mean) ** 2 for g in gaps) / len(gaps)

    return {
        "minimize_dancers_moved": changed,
        "minimize_total_distance": round(total, 8),
        "symmetry": round(symmetry + 0.25 * uneven, 8),
        "preserve_center": round(center_movement, 8),
    }


def rank_candidates(source, missing, candidates, requirements):
    """Filter invalid or nonconforming routines, then lexicographically rank.

    The primary priority takes precedence over all secondary objectives.
    A hard max_dancers_moved removes candidates *before* scoring.
    """
    from app.repair import validate

    req = validate_ai_requirements(requirements)
    if not any(p["id"] == missing for f in source["formations"] for p in f["dancers"]):
        raise ValueError(f"Unknown dancer: {missing}")
    if validate(source):
        raise ValueError("Cannot optimize an invalid source routine.")

    ranked = []
    max_moved = req["constraints"].get("max_dancers_moved")
    priority_order = [req["primary_priority"], *req["secondary_priorities"]]
    # Deterministic fallback tie breakers do not supersede the captain's goals.
    priority_order += [p for p in (
        "minimize_dancers_moved", "minimize_total_distance", "symmetry", "preserve_center"
    ) if p not in priority_order]

    for option in candidates:
        if not isinstance(option, dict) or not isinstance(option.get("label"), str):
            continue
        routine = option.get("routine")
        if not _has_correct_roster(source, missing, routine):
            continue
        if validate(routine, missing):
            continue
        scores = _metrics(source, option)
        if max_moved is not None and scores["minimize_dancers_moved"] > max_moved:
            continue
        clean_option = deepcopy(option)
        clean_option["score_breakdown"] = {
            "symmetry_error": scores["symmetry"],
            "moved_dancers": scores["minimize_dancers_moved"],
            "total_displacement": scores["minimize_total_distance"],
            "center_displacement": scores["preserve_center"],
        }
        key = tuple(scores[p] for p in priority_order)
        ranked.append((key, clean_option))

    # Stable sorting preserves candidate-generation order for complete ties.
    ranked.sort(key=lambda item: item[0])
    return [option for _, option in ranked]


def _without_missing(source, missing):
    candidate = deepcopy(source)
    for f in candidate["formations"]:
        f["dancers"] = [p for p in f["dancers"] if p["id"] != missing]
    return candidate


def _center_affected_horizontal_rows(source, missing, center_choice):
    """A genuine geometry alternative: center each affected horizontal row.

    Uses the original row's median spacing. Rows not containing the absent
    dancer remain untouched; candidates that collide are removed by ranking.
    """
    candidate = _without_missing(source, missing)
    updated = False
    for before, after in zip(source["formations"], candidate["formations"]):
        absent = next((p for p in before["dancers"] if p["id"] == missing), None)
        if absent is None:
            continue
        # A row must be nearly horizontal and must have included >=3 dancers.
        original_row = [p for p in before["dancers"] if abs(p["y"] - absent["y"]) < 0.15]
        if len(original_row) < 3:
            continue
        remaining_ids = {p["id"] for p in original_row if p["id"] != missing}
        survivors = sorted((p for p in after["dancers"] if p["id"] in remaining_ids),
                           key=lambda p: (p["x"], p["id"]))
        if len(survivors) < 2:
            continue
        old_x = sorted(p["x"] for p in original_row)
        gaps = [b - a for a, b in zip(old_x, old_x[1:])]
        if not gaps or min(gaps) < 0.6 or max(gaps) - min(gaps) > 0.2 * median(gaps):
            continue
        spacing = median(gaps)
        center = (source["stage"]["width"] / 2 if center_choice == "stage"
                  else (min(old_x) + max(old_x)) / 2)
        # Avoid designing positions outside stage boundaries.
        if (center - spacing * (len(survivors) - 1) / 2 < 0
                or center + spacing * (len(survivors) - 1) / 2 > source["stage"]["width"]):
            continue
        for i, p in enumerate(survivors):
            p["x"] = round(center + (i - (len(survivors) - 1) / 2) * spacing, 4)
        updated = True
    return candidate if updated else None


def _generate_candidates(source, missing):
    from app.repair import repair

    items = [{"label": "Fewest changes (remove only)",
              "routine": _without_missing(source, missing)}]
    for preference, label in [
        ("minimize_changes", "Legacy minimize changes"),
        ("preserve_center", "Legacy preserve center"),
    ]:
        old_result = repair(source, missing, preference)
        if old_result.get("valid"):
            items.append({"label": label, "routine": old_result["routine"]})

    for center_choice in ("stage", "original"):
        variant = _center_affected_horizontal_rows(source, missing, center_choice)
        if variant is not None:
            items.append({"label": f"Center affected rows: {center_choice}",
                          "routine": variant})

    # Avoid offering identical placements with different labels.
    fingerprints = set()
    unique = []
    for option in items:
        coords = tuple(tuple((p["id"], p["x"], p["y"])
                             for p in f["dancers"])
                       for f in option["routine"]["formations"])
        if coords not in fingerprints:
            fingerprints.add(coords)
            unique.append(option)
    return unique


def repair_with_requirements(source, missing, requirements):
    """Choose one validated AI-priority-aware repair (Part 1).

    Part 2 will expose the ranked candidates as three UI suggestions.
    """
    from app.repair import validate

    req = validate_ai_requirements(requirements)
    ranked = rank_candidates(source, missing, _generate_candidates(source, missing), req)
    if not ranked:
        raise ValueError("No valid repair satisfies these requirements.")
    chosen = ranked[0]
    metrics = chosen["score_breakdown"]
    routine = chosen["routine"]
    errors = validate(routine, missing)
    return {
        "routine": routine,
        "valid": not errors,
        "errors": errors,
        "alternatives": [],  # Part 2 adds multiple selectable suggestions.
        "changed_assignments": metrics["moved_dancers"],
        "total_displacement": round(metrics["total_displacement"], 4),
        "score_breakdown": metrics,
        "candidate_label": chosen["label"],
        "method": "AI priority-aware validated selection",
        "note": (
            f"Chosen for {req['primary_priority']}; evaluated "
            f"{len(ranked)} valid candidate layout(s). "
            "Transitions and choreography still require captain review."
        ),
    }
