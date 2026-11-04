
"""Send formation repair instructions to an AI model."""

from openai import OpenAI

from app.openai_adapter import parse_llm_preference


def get_ai_preference(instruction: str, client=None) -> dict:
    # Check that the instruction is not empty
    if not instruction or not instruction.strip():
        raise ValueError("Please enter a repair instruction.")

    # Create an OpenAI client if one was not provided
    if client is None:
        client = OpenAI()

    # Tell the AI which repair preferences are supported
    system_prompt = (
        "You interpret dance formation repair instructions. "
        "Choose exactly one preference: "
        "'minimize_changes' or 'preserve_center'. "
        "Use 'preserve_center' when the user wants to keep "
        "middle or center dancers in place. "
        "Otherwise use 'minimize_changes' for requests "
        "to reduce dancer movement or changes. "
        "Return only a JSON object with a preference field. "
        "Example: {\"preference\": \"preserve_center\"}"
    )

    # Send the instruction to the AI model
    response = client.responses.create(
        model="gpt-6-luna",
        instructions=system_prompt,
        input=instruction
    )

    # Parse and validate the AI response
    return parse_llm_preference(response.output_text)
