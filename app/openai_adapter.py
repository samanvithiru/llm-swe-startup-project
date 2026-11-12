"""Parse and validate AI-generated formation preferences and requirements."""

import json

from app.llm_preferences import SUPPORTED_PREFERENCES
from app.ai_requirements import parse_ai_requirements  # New advanced AI contract


def parse_llm_preference(response: str) -> dict:
    """Legacy two-option manual/AI interpreter: kept backward-compatible."""
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("The AI returned invalid JSON.")

    if not isinstance(data, dict):
        raise ValueError("The AI response must be an object.")

    preference = data.get("preference")
    if preference not in SUPPORTED_PREFERENCES:
        raise ValueError("Unsupported AI repair preference.")

    return {"preference": preference}
