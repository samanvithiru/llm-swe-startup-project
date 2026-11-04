"""Deterministic, testable formation repair for a single unavailable dancer."""
from __future__ import annotations
from math import dist


def validate(routine: dict, missing: str | None = None, min_spacing: float = 0.6) -> list[str]:
    errors = []
    width, height = routine['stage']['width'], routine['stage']['height']
    for fi, formation in enumerate(routine['formations']):
        dancers = formation['dancers']
        ids = [p['id'] for p in dancers]
        if len(ids) != len(set(ids)):
            errors.append(f'Formation {fi + 1}: duplicate dancer ID')
        if missing and missing in ids:
            errors.append(f'Formation {fi + 1}: unavailable dancer remains')
        for p in dancers:
            if not (0 <= p['x'] <= width and 0 <= p['y'] <= height):
                errors.append(f"Formation {fi + 1}: {p['id']} outside stage")
        for i, a in enumerate(dancers):
            for b in dancers[i + 1:]:
                if dist((a['x'], a['y']), (b['x'], b['y'])) < min_spacing:
                    errors.append(f"Formation {fi + 1}: {a['id']} and {b['id']} too close")
    return errors


def repair(routine: dict, missing: str, preference: str = 'minimize_changes') -> dict:
    """Remove one dancer while leaving their previous position vacant.

    Each formation retains all other dancer IDs. This is an Alpha baseline,
    not global pathfinding or an artistic formation repair.
    """
    if not any(p['id'] == missing for f in routine['formations'] for p in f['dancers']):
        raise ValueError(f'Unknown dancer: {missing}')
    if preference not in ('minimize_changes', 'preserve_center'):
        raise ValueError('Unsupported preference')
    result = {'stage': dict(routine['stage']), 'formations': []}
    for formation in routine['formations']:
        people = [dict(p) for p in formation['dancers'] if p['id'] != missing]
        # Preserve every remaining dancer's learned position: zero reassignment.
        # The missing position is intentionally vacant, rather than inventing a replacement.
        result['formations'].append({'name': formation['name'], 'dancers': people})
    errors = validate(result, missing)
    return {'routine': result, 'valid': not errors, 'errors': errors,
            'changed_assignments': 0, 'removed_dancer': missing,
            'method': 'vacancy-preserving baseline',
            'note': 'This baseline removes the absent dancer but does not close formation gaps or optimize transitions.'}
