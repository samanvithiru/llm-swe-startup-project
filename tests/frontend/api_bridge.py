"""JSON bridge from Node workflow checks to the actual in-process FastAPI app.

The Gemini boundary is replaced to avoid API keys, billing, and network access.
Request validation, HTTP routing, repair, and response serialization are real.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi.testclient import TestClient
import app.server as server


def fake_ai(instruction):
    if not instruction.strip():
        raise ValueError("Please enter a repair instruction.")
    return {"preference": "preserve_center"}


server.get_ai_preference = fake_ai
request = json.load(sys.stdin)
with TestClient(server.app) as client:
    response = client.post(request["url"], json=request["body"])
print(json.dumps({"status": response.status_code, "body": response.json()}))
