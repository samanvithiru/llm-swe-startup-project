
"""Validate preferences returned by an LLM."""

# Preferences supported by the repair algorithm
SUPPORTED_PREFERENCES = {
    "minimize_changes",
    "preserve_center",
}


def interpret_with_llm(instruction: str, llm_call) -> dict:
    # Reject empty instructions
    if not instruction or not instruction.strip():
        raise ValueError("Please enter a repair instruction.")

    # Ask the LLM to interpret the instruction
    response = llm_call(instruction)

    # Check that the LLM returned a dictionary
    if not isinstance(response, dict):
        raise ValueError("Invalid LLM response format.")

    # Get the preference from the response
    preference = response.get("preference")

    # Reject unsupported or missing preferences
    if preference not in SUPPORTED_PREFERENCES:
        raise ValueError("Unsupported LLM repair preference.")

    # Return only the validated preference
    return {"preference": preference}
