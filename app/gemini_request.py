
"""Send formation repair instructions to Google Gemini."""

import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai.errors import ServerError

from app.openai_adapter import parse_llm_preference

# Load the API key and model settings
load_dotenv()


def get_gemini_preference(instruction: str, client=None) -> dict:
    # Make sure the captain entered an instruction
    if not instruction or not instruction.strip():
        raise ValueError("Please enter a repair instruction.")

    # Create the Gemini client using our API key
    if client is None:
        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is missing from .env")

        client = genai.Client(api_key=api_key)

    # Explain which repair preferences Gemini can select
    system_prompt = (
        "You interpret dance formation repair instructions. "
        "Choose exactly one preference: "
        "'minimize_changes' or 'preserve_center'. "
        "Choose 'preserve_center' when the user wants to keep "
        "middle or center dancers in place. "
        "Otherwise choose 'minimize_changes'. "
        "Return only JSON, for example: "
        '{"preference": "preserve_center"}'
    )

    # Retry if Gemini is temporarily unavailable
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
                contents=(
                    system_prompt
                    + "\n\nUser instruction: "
                    + instruction
                ),
            )
            break

        except ServerError as exc:
            # Only retry temporary server errors
            if exc.code not in (500, 502, 503, 504) or attempt == 2:
                raise

            time.sleep(2 ** attempt)

    # Convert Gemini's answer into a validated preference
    return parse_llm_preference(response.text)
