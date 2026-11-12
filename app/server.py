"""FormationRescue web API: unchanged manual flow, plus advanced AI repair."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .repair import repair, validate
from .pdf_import import MAX_PDF_BYTES, PDFImportError, import_sway_pdf
from .gemini_request import (
    get_gemini_preference as get_ai_preference,
    get_gemini_requirements as get_ai_requirements,
)
from .priority_repair import repair_with_requirements

app = FastAPI(title="FormationRescue Alpha")


class RepairRequest(BaseModel):
    routine: dict
    missing: str
    preference: str = "minimize_changes"


class AIPreferenceRequest(BaseModel):
    instruction: str


class AdvancedAIRepairRequest(BaseModel):
    routine: dict
    missing: str
    instruction: str


@app.get("/")
def home():
    return FileResponse(Path(__file__).with_name("index.html"))


# The two manual preferences continue through the original endpoint.
@app.post("/api/repair")
def repair_api(request: RepairRequest):
    try:
        source_errors = validate(request.routine)
        if source_errors:
            raise HTTPException(status_code=422, detail=source_errors)
        return repair(request.routine, request.missing, request.preference)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# Retain the original two-choice Gemini endpoint for backwards compatibility.
@app.post("/api/ai-preference")
def ai_preference_api(request: AIPreferenceRequest):
    try:
        return get_ai_preference(request.instruction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=503, detail="AI service is currently unavailable."
        ) from exc


@app.post("/api/repair-ai")
def repair_ai_api(request: AdvancedAIRepairRequest):
    """A separate natural-language-to-layout path; never change manual mode."""
    if not request.instruction or not request.instruction.strip():
        raise HTTPException(status_code=400, detail="Please enter a repair instruction.")

    try:
        source_errors = validate(request.routine)
        if source_errors:
            raise HTTPException(status_code=422, detail=source_errors)
        if not any(p["id"] == request.missing
                   for f in request.routine["formations"] for p in f["dancers"]):
            raise ValueError(f"Unknown dancer: {request.missing}")
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    # Only the Gemini call should turn into a service-unavailable error.
    try:
        requirements = get_ai_requirements(request.instruction)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=503, detail="AI service is currently unavailable."
        ) from exc

    try:
        result = repair_with_requirements(
            request.routine, request.missing, requirements
        )
    except (ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {**result, "requirements": requirements}


@app.post("/api/import/sway-pdf")
def import_pdf_api(file: UploadFile):
    """Extract a reviewable draft; do not repair or store uploaded PDF."""
    try:
        content = file.file.read(MAX_PDF_BYTES + 1)
        if len(content) > MAX_PDF_BYTES:
            raise HTTPException(
                status_code=413, detail="PDF exceeds the 10 MB upload limit."
            )
        return import_sway_pdf(content)
    except PDFImportError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        file.file.close()
