
"""Structure-preserving repair for PDF-imported dance formations.

Symmetry and even spacing are prioritized; dancer movement is a tiebreaker.
Never moves a dancer between detected rows/columns or invents arbitrary clusters.
Uses only the standard library; preserves repair_pdf_formation's public API.
"""
from __future__ import annotations

from math import hypot, atan2, cos, sin


def _distance(a, b):
    return hypot(a['x'] - b['x'], a['y'] - b['y'])


def _cluster(points, coordinate, tolerance):
    groups = []
    for p in sorted(points, key=lambda q: (q[coordinate], q['id'])):
        choices = [(abs(p[coordinate] - sum(q[coordinate] for q in group) / len(group)), i)
                   for i, group in enumerate(groups)]
        if choices and min(choices)[0] <= tolerance:
            groups[min(choices)[1]].append(p)
        else:
            groups.append([p])
    return groups


def _median(values):
    values = sorted(values)
    if not values:
        return 0.0
    n = len(values)
    return (values[(n - 1) // 2] + values[n // 2]) / 2


def _nearest_gap(points):
    distances = [min(_distance(p, q) for q in points if q is not p)
                 for p in points] if len(points) > 1 else [2.0]
    return max(0.65, _median(distances))


def _valid(points, stage):
    if any(not (0 <= p['x'] <= stage['width'] and 0 <= p['y'] <= stage['height'])
           for p in points):
        return False
    return all(_distance(a, b) >= 0.6 - 1e-6
               for i, a in enumerate(points) for b in points[i + 1:])


def _direction(group):
    """Principal axis, for coherent diagonal groups."""
    cx = sum(p['x'] for p in group) / len(group)
    cy = sum(p['y'] for p in group) / len(group)
    xx = sum((p['x'] - cx) ** 2 for p in group)
    yy = sum((p['y'] - cy) ** 2 for p in group)
    xy = sum((p['x'] - cx) * (p['y'] - cy) for p in group)
    angle = 0.5 * atan2(2 * xy, xx - yy)
    return cos(angle), sin(angle)


def _linearity(group):
    if len(group) < 3:
        return 0.0
    vx, vy = _direction(group)
    cx = sum(p['x'] for p in group) / len(group)
    cy = sum(p['y'] for p in group) / len(group)
    along = sum(((p['x'] - cx) * vx + (p['y'] - cy) * vy) ** 2 for p in group)
    across = sum((-(p['x'] - cx) * vy + (p['y'] - cy) * vx) ** 2 for p in group)
    return along / max(along + across, 1e-9)


def _reflow(group, missing, axis, center_mode, width_factor=1.0):
    """Rebuild equally spaced slots along an existing structural line.

    Keep dancers in their group and in their original order.
    """
    survivors = [p for p in group if p['id'] != missing]
    if len(survivors) < 2:
        return {}
    if axis == 'x':
        vx, vy = 1.0, 0.0
    elif axis == 'y':
        vx, vy = 0.0, 1.0
    else:
        vx, vy = _direction(group)
    cx = sum(p['x'] for p in group) / len(group)
    cy = sum(p['y'] for p in group) / len(group)
    project = lambda p: (p['x'] - cx) * vx + (p['y'] - cy) * vy
    ordered = sorted(survivors, key=lambda p: (project(p), p['id']))
    old_positions = sorted(project(p) for p in group)
    span = (old_positions[-1] - old_positions[0]) * width_factor
    if span < 0.6 * (len(ordered) - 1):
        return {}
    if center_mode == 'original':
        center = (old_positions[0] + old_positions[-1]) / 2
    else:
        center = _median([project(p) for p in survivors])
    start = center - span / 2
    updates = {}
    for i, p in enumerate(ordered):
        desired = start + i * span / (len(ordered) - 1)
        change = desired - project(p)
        updates[p['id']] = {'x': round(p['x'] + change * vx, 4),
                            'y': round(p['y'] + change * vy, 4)}
    return updates


def _apply(original, updates):
    return [{**p, **updates.get(p['id'], {})} for p in original]


def _symmetry(group, axis, center):
    if not group:
        return 0.0
    # Matching with same transverse coordinate prevents unrelated rows from
    # being treated as symmetric partners.
    total = 0.0
    for p in group:
        if axis == 'x':
            rx, ry = 2 * center - p['x'], p['y']
        else:
            rx, ry = p['x'], 2 * center - p['y']
        total += min(hypot(q['x'] - rx, q['y'] - ry) for q in group)
    return total / len(group)


def _quality(points, original, groups, axis, preference, stage):
    by_id = {p['id']: p for p in points}
    old = {p['id']: p for p in original}
    total = sum(_distance(p, old[p['id']]) for p in points)
    moved = sum(_distance(p, old[p['id']]) > 0.15 for p in points)
    uneven = 0.0
    mirror = 0.0
    for group in groups:
        surviving = [by_id[p['id']] for p in group if p['id'] in by_id]
        if len(surviving) < 2:
            continue
        center = (min(p[axis] for p in group) + max(p[axis] for p in group)) / 2
        ordered = sorted(surviving, key=lambda p: p[axis])
        gaps = [b[axis] - a[axis] for a, b in zip(ordered, ordered[1:])]
        average = sum(gaps) / len(gaps)
        uneven += sum((g - average) ** 2 for g in gaps) / max(len(gaps), 1)
        mirror += _symmetry(surviving, axis, center)
    center_cost = (sum(hypot(p['x'] - stage['width']/2, p['y'] - stage['height']/2)
                       for p in points) * 0.001 if preference == 'preserve_center' else 0)
    # Compare geometry first; movement matters only once the shape is clean.
    score = 5 * uneven + 2 * mirror + 0.08 * moved + 0.025 * total + center_cost
    return score, {'symmetry_error': round(mirror, 4),
                   'row_spacing_error': round(uneven, 4),
                   'moved_dancers': moved,
                   'total_displacement': round(total, 4),
                   'spacing_penalty': 0.0}


def repair_pdf_formation(formation, missing, preference, stage):
    """Repair the affected structural group, favoring symmetry over movement.

    For structured rows/columns, redistribute only the affected group. For a
    single coherent diagonal, redistribute along its own axis. For genuinely
    irregular clusters, keep the safe baseline instead of mangling the shape.
    """
    original_all = formation['dancers']
    original = [dict(p) for p in original_all if p['id'] != missing]
    absent = next((p for p in original_all if p['id'] == missing), None)
    if absent is None or not original:
        return original, {}
    gap = _nearest_gap(original_all)
    tolerance = max(0.3, min(1.25, gap * 0.27))
    options = []
    for axis, group_key in [('x', 'y'), ('y', 'x')]:
        groups = _cluster(original_all, group_key, tolerance)
        affected = next((g for g in groups if absent in g), None)
        if affected is None or len(affected) < 3:
            continue
        # A grouping must describe an actual row/column, not a random clump.
        spread = max(p[axis] for p in affected) - min(p[axis] for p in affected)
        transverse = max(p[group_key] for p in affected) - min(p[group_key] for p in affected)
        if spread < max(1.0, 2 * transverse):
            continue
        for width_factor in (1.0, 0.90, 0.80):
            for center_mode in ('original', 'survivors'):
                updates = _reflow(affected, missing, axis, center_mode, width_factor)
                if updates:
                    options.append((axis, groups, updates, f'{group_key}-aligned rebalancing'))
    # A diagonal is eligible only if the entire formation is nearly collinear.
    if len(original_all) >= 4 and _linearity(original_all) >= 0.97:
        for width_factor in (1.0, 0.90):
            updates = _reflow(original_all, missing, 'diagonal', 'original', width_factor)
            if updates:
                options.append(('x', [original_all], updates, 'diagonal rebalancing'))
    if not options:
        return original, {'method': 'preserve irregular formation',
                          'candidates_evaluated': 0,
                          'repaired': {'moved_dancers': 0, 'total_displacement': 0.0}}
    # Use the structure that actually produced candidates, and do not reward
    # the remove-only baseline just because it requires zero movement.
    ranked = []
    for axis, groups, updates, label in options:
        candidate = _apply(original, updates)
        if not _valid(candidate, stage):
            continue
        score, metrics = _quality(candidate, original, groups, axis, preference, stage)
        baseline, baseline_metrics = _quality(original, original, groups, axis, preference, stage)
        improvement = baseline - score
        # A geometric improvement must outweigh any increase in movement.
        if improvement <= 0.001:
            continue
        ranked.append((score - baseline, metrics['moved_dancers'],
                       metrics['total_displacement'], label, candidate,
                       baseline, score, baseline_metrics, metrics))
    if not ranked:
        return original, {'method': 'remove-only baseline (no valid improvement)',
                          'candidates_evaluated': len(options),
                          'repaired': {'moved_dancers': 0, 'total_displacement': 0.0}}
    ranked.sort(key=lambda r: (r[0], r[1], r[2]))
    _, _, _, label, best, baseline, score, before, after = ranked[0]
    return best, {'method': label, 'candidates_evaluated': len(options),
                  'baseline_score': round(baseline, 4),
                  'repaired_score': round(score, 4),
                  'improvement_percent': round(100 * (baseline-score)/max(baseline, 1e-9), 2),
                  'baseline': before, 'repaired': after}
