
"""Parse and validate AI-generated formation preferences."""

import json

from app.llm_preferences import SUPPORTED_PREFERENCES


def parse_llm_preference(response: str) -> dict:
    # Convert the AI response from JSON text into Python
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        raise ValueError("The AI returned invalid JSON.")

    # Make sure the response is a dictionary
    if not isinstance(data, dict):
        raise ValueError("The AI response must be an object.")

    # Get the preference from the response
    preference = data.get("preference")

    # Check that the preference is supported
    if preference not in SUPPORTED_PREFERENCES:
        raise ValueError("Unsupported AI repair preference.")

    # Return the validated preference
    return {"preference": preference}
