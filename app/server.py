
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .repair import repair, validate
from .pdf_import import MAX_PDF_BYTES, PDFImportError, import_sway_pdf
from .gemini_request import get_gemini_preference as get_ai_preference

app = FastAPI(title="FormationRescue Alpha")


# Store the information needed to repair a routine
class RepairRequest(BaseModel):
    routine: dict
    missing: str
    preference: str = "minimize_changes"


# Store the dance captain's AI instruction
class AIPreferenceRequest(BaseModel):
    instruction: str


# Display the FormationRescue website
@app.get("/")
def home():
    return FileResponse(Path(__file__).with_name("index.html"))


# Repair a formation using the selected preference
@app.post("/api/repair")
def repair_api(request: RepairRequest):
    try:
        source_errors = validate(request.routine)

        if source_errors:
            raise HTTPException(
                status_code=422,
                detail=source_errors
            )

        return repair(
            request.routine,
            request.missing,
            request.preference
        )

    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc


# Interpret natural-language instructions using AI
@app.post("/api/ai-preference")
def ai_preference_api(request: AIPreferenceRequest):
    try:
        # Ask the AI to interpret the instruction
        result = get_ai_preference(request.instruction)

        # Return the supported repair preference
        return result

    except ValueError as exc:
        # Reject empty or invalid instructions
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        ) from exc

    except Exception as exc:
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=503,
            detail="AI service is currently unavailable."
        ) from exc


@app.post("/api/import/sway-pdf")
def import_pdf_api(file: UploadFile):
    """Extract a reviewable draft; do not repair or store the uploaded PDF."""
    try:
        content = file.file.read(MAX_PDF_BYTES + 1)
        if len(content) > MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail="PDF exceeds the 10 MB upload limit.")
        return import_sway_pdf(content)
    except PDFImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        file.file.close()
