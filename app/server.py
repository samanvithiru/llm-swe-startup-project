from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .repair import repair, validate

app = FastAPI(title='FormationRescue Alpha')

class RepairRequest(BaseModel):
    routine: dict
    missing: str
    preference: str = 'minimize_changes'

@app.get('/')
def home():
    return FileResponse(Path(__file__).with_name('index.html'))

@app.post('/api/repair')
def repair_api(request: RepairRequest):
    try:
        source_errors = validate(request.routine)
        if source_errors:
            raise HTTPException(status_code=422, detail=source_errors)
        return repair(request.routine, request.missing, request.preference)
    except (KeyError, TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
