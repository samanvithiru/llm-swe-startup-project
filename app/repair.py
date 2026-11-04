"""Deterministic, testable formation repair for a single unavailable dancer."""
from __future__ import annotations
from math import dist



def validate(routine: dict, missing: str | None = None, min_spacing: float = 0.6) -> list[str]:
    errors = []
    width, height = routine['stage']['width'], routine['stage']['height']

    # Check that every formation has the same dancers
    if routine['formations']:
        expected_ids = {
            p['id'] for p in routine['formations'][0]['dancers']
        }

        for fi, formation in enumerate(routine['formations'][1:], start=2):
            current_ids = {
                p['id'] for p in formation['dancers']
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

    # Check each formation for invalid dancer positions
    for fi, formation in enumerate(routine['formations']):
        dancers = formation['dancers']
        ids = [p['id'] for p in dancers]

        # Check for duplicate dancer IDs
        if len(ids) != len(set(ids)):
            errors.append(f'Formation {fi + 1}: duplicate dancer ID')

        # Check if the unavailable dancer is still present
        if missing and missing in ids:
            errors.append(f'Formation {fi + 1}: unavailable dancer remains')

        # Check that dancers are inside the stage
        for p in dancers:
            if not (0 <= p['x'] <= width and 0 <= p['y'] <= height):
                errors.append(
                    f"Formation {fi + 1}: {p['id']} outside stage"
                )

        # Check that dancers are not too close together
        for i, a in enumerate(dancers):
            for b in dancers[i + 1:]:
                if dist((a['x'], a['y']), (b['x'], b['y'])) < min_spacing:
                    errors.append(
                        f"Formation {fi + 1}: {a['id']} and {b['id']} too close"
                    )

    return errors


def repair(routine: dict, missing: str, preference: str = 'minimize_changes') -> dict:
    """Close vacancies with a small deterministic, spacing-checked local adjustment.

    This is a geometric heuristic, not a global choreography or transition solver.
    """
    if not any(p['id'] == missing for f in routine['formations'] for p in f['dancers']):
        raise ValueError(f'Unknown dancer: {missing}')
    if preference not in ('minimize_changes', 'preserve_center'):
        raise ValueError('Unsupported preference')
    result = {'stage': dict(routine['stage']), 'formations': []}
    moved = 0
    displacement = 0.0
    for formation in routine['formations']:
        missing_positions = [p for p in formation['dancers'] if p['id'] == missing]
        people = [dict(p) for p in formation['dancers'] if p['id'] != missing]
        if missing_positions and people:
            vacant = missing_positions[0]
            # Move dancers slightly toward the vacant position, weighting closer
            # dancers more heavily. Try progressively smaller adjustments until
            # the deterministic validator accepts the entire candidate.
            from math import hypot
            distances = [hypot(p['x'] - vacant['x'], p['y'] - vacant['y']) for p in people]
            nearest = min(distances)
            for strength in (0.24, 0.16, 0.10, 0.05, 0.02):
                candidate = [dict(p) for p in people]
                for p, d in zip(candidate, distances):
                    weight = strength * (nearest / max(d, 0.00001))
                    if preference == 'preserve_center':
                        # Prefer to keep dancers close to stage center unchanged.
                        center_distance = hypot(p['x'] - routine['stage']['width']/2,
                                                p['y'] - routine['stage']['height']/2)
                        weight *= min(1.0, center_distance / 2.0)
                    p['x'] = round(p['x'] + (vacant['x'] - p['x']) * weight, 4)
                    p['y'] = round(p['y'] + (vacant['y'] - p['y']) * weight, 4)
                trial = {'stage': result['stage'], 'formations': [{'name': formation['name'], 'dancers': candidate}]}
                if not validate(trial):
                    people = candidate
                    break
        before = {p['id']: p for p in formation['dancers']}
        for p in people:
            delta = dist((p['x'], p['y']), (before[p['id']]['x'], before[p['id']]['y']))
            if delta > 0.00001:
                moved += 1
                displacement += delta
        result['formations'].append({'name': formation['name'], 'dancers': people})
    errors = validate(result, missing)
    return {'routine': result, 'valid': not errors, 'errors': errors,
            'changed_assignments': moved, 'total_displacement': round(displacement, 4),
            'removed_dancer': missing, 'method': 'spacing-checked local reblocking',
            'note': 'Local geometric repair only; choreography directions and transition feasibility require captain review.'}
