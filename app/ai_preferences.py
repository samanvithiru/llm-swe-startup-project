
"""Interpret dance formation repair preferences."""

def interpret_preference(instruction: str) -> dict:
    # Check for empty instructions
    if not instruction or not instruction.strip():
        raise ValueError("Please enter a repair instruction.")

    text = instruction.lower().strip()

    # Check for preferences about keeping center dancers
    if "center" in text or "middle" in text:
        return {"preference": "preserve_center"}

    # Check for preferences about minimizing movement
    if "minimize" in text or "least movement" in text:
        return {"preference": "minimize_changes"}

    # Reject instructions we do not support
    raise ValueError("Unsupported repair instruction.")
