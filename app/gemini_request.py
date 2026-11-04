
"""Send formation repair instructions to Google Gemini."""

from google import genai
from dotenv import load_dotenv

from app.openai_adapter import parse_llm_preference

# Load the private API key from the project .env file
load_dotenv()


def get_gemini_preference(instruction: str, client=None) -> dict:
    # Check that the instruction is not empty
    if not instruction or not instruction.strip():
        raise ValueError("Please enter a repair instruction.")

    # Create a Gemini client if one was not provided
    if client is None:
        client = genai.Client()

    # Tell Gemini which repair preferences are supported
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

    # Send the instruction to Gemini
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=system_prompt + "\n\nUser instruction: " + instruction
    )

    # Parse and validate Gemini's response
    return parse_llm_preference(response.text)
