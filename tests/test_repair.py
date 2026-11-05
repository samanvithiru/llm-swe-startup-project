import pytest
from app.repair import repair, validate

@pytest.fixture
def routine():
    return {'stage': {'width': 10, 'height': 6}, 'formations': [
        {'name': 'Line', 'dancers': [{'id': 'A', 'x': 1, 'y': 1}, {'id': 'B', 'x': 3, 'y': 1}, {'id': 'C', 'x': 5, 'y': 1}]},
        {'name': 'Triangle', 'dancers': [{'id': 'A', 'x': 2, 'y': 2}, {'id': 'B', 'x': 4, 'y': 2}, {'id': 'C', 'x': 3, 'y': 4}]}
    ]}

def test_removes_absent_dancer_from_every_formation(routine):
    result = repair(routine, 'B')
    assert result['valid']
    assert all('B' not in [p['id'] for p in f['dancers']] for f in result['routine']['formations'])


def test_does_not_mutate_original(routine):
    from copy import deepcopy

    original = deepcopy(routine)

    # Test both supported repair preferences
    for preference in ["minimize_changes", "preserve_center"]:
        result = repair(routine, "B", preference)

        # Original routine must remain completely unchanged
        assert routine == original

        # The repaired copy must exclude the missing dancer
        for formation in result["routine"]["formations"]:
            ids = [p["id"] for p in formation["dancers"]]

            assert "B" not in ids
            assert set(ids) == {"A", "C"}

        # The original should still contain all dancers
        assert all(
            len(f["dancers"]) == 3
            for f in routine["formations"]
        )


def test_unknown_dancer_rejected(routine):
    with pytest.raises(ValueError, match='Unknown dancer'):
        repair(routine, 'Z')

def test_unsupported_preference_rejected(routine):
    with pytest.raises(ValueError, match='Unsupported'):
        repair(routine, 'B', 'do_anything')

def test_detects_out_of_bounds(routine):
    routine['formations'][0]['dancers'][0]['x'] = 99
    assert any('outside stage' in e for e in validate(routine))

def test_detects_spacing_violation(routine):
    routine['formations'][0]['dancers'][1]['x'] = 1.2
    assert any('too close' in e for e in validate(routine))

def test_detects_duplicate_id(routine):
    routine['formations'][0]['dancers'][1]['id'] = 'A'
    assert any('duplicate' in e for e in validate(routine))
