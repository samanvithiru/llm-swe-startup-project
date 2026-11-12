"""Validate structured, captain-specified AI repair requirements.

A requirement is one PRIMARY objective, ordered optional SECONDARY objectives,
and HARD constraints. Do not silently invent or drop unsupported instructions.
"""

import json

SUPPORTED_PRIORITIES = frozenset({
    "symmetry", "minimize_dancers_moved", "minimize_total_distance", "preserve_center"
})
SUPPORTED_CONSTRAINTS = frozenset({"max_dancers_moved"})


def validate_ai_requirements(data):
    """Return a canonical dict or raise ValueError (never silently coerce)."""
    if not isinstance(data, dict):
        raise ValueError("AI requirements must be a JSON object.")
    if set(data) != {"primary_priority", "secondary_priorities", "constraints"}:
        raise ValueError("AI requirements must contain exactly the three required fields.")

    primary = data["primary_priority"]
    secondary = data["secondary_priorities"]
    constraints = data["constraints"]
    if not isinstance(primary, str) or primary not in SUPPORTED_PRIORITIES:
        raise ValueError("Unsupported primary AI priority.")
    if not isinstance(secondary, list) or any(
        not isinstance(p, str) or p not in SUPPORTED_PRIORITIES for p in secondary
    ):
        raise ValueError("Unsupported secondary AI priority.")
    if len(set(secondary)) != len(secondary) or primary in secondary:
        raise ValueError("Priorities cannot be repeated or conflict with one another.")
    if not isinstance(constraints, dict):
        raise ValueError("AI constraints must be an object.")
    if set(constraints) - SUPPORTED_CONSTRAINTS:
        raise ValueError("Unsupported AI constraint.")
    if "max_dancers_moved" in constraints:
        n = constraints["max_dancers_moved"]
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError("max_dancers_moved must be a non-negative integer.")

    return {
        "primary_priority": primary,
        "secondary_priorities": list(secondary),
        "constraints": dict(constraints),
    }


def parse_ai_requirements(response):
    """Parse exactly one JSON object returned by Gemini."""
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("The AI returned invalid requirements JSON.") from exc
    return validate_ai_requirements(data)
