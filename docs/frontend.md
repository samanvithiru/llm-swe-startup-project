# Frontend workflow — US-1, US-2, US-6

Run from the repository root:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.server:app --reload
```

Open http://127.0.0.1:8000. No frontend build or npm dependencies are needed.

## Load and select (US-1 and US-2)

**Sway PDF upload is now the primary import workflow.** See [PDF import](pdf-import.md) for supported exports, preview/confirmation, offstage-page handling, and tests. The app starts empty and accepts PDF imports; example routines, automatic demo loading, and JSON input/help have been removed. Routine backups and review exports remain available.

Upload and confirm a PDF before generating a repair. Every included formation appears with its exact PDF label; the unavailable-dancer selector uses the imported names. Loading another routine or selecting another absent dancer clears the proposal and cancels pending requests.

The interface uses a black background, white text, purple dancer markers, and pale-purple movement outlines/paths. Unavailable or offstage dancers remain pink/red to distinguish them. Preview, original, and repaired diagrams share a stage-coordinate grid read from the PDF axes. Kuthu's four depth divisions and Bhangra's three are preserved; grid lines do not move or rescale dancers. The importer adds numeric grid metadata without changing the repair algorithm.

Imports require positive finite stage dimensions, named nonempty formations, unique nonempty string IDs within each formation, finite coordinates within the stage, and the same dancer roster in every formation. Failed imports preserve the previous routine. Source spacing validation remains the backend's responsibility. Frontend checks supplement the API; they do not replace server-side schema validation, which remains incomplete.

The selected absence is sent to the existing POST /api/repair endpoint as `{routine, missing, preference}`. Manual preferences are `minimize_changes` and `preserve_center`. AI-guided repair first calls `POST /api/ai-preference` with `{instruction}`, validates the returned preference, then requests a repair. Changing the routine, absence, preference, or instruction cancels pending work. AI failures leave manual controls available. The client checks that the returned roster in each formation is the original roster minus that dancer before displaying the proposal.

The server uses Gemini for interpretation and requires a locally configured `GEMINI_API_KEY` (environment or ignored `.env`) for live AI requests. Never put a key in HTML or commit it. The normal repair endpoint requires no AI credentials. Gemini requests default to `gemini-3.8-flash`; set `GEMINI_MODEL` in the environment or `.env` to override it. AI currently chooses a supported preference; it does not generate layouts or minimize left/right choreography switches. Shape-specific repairs may follow their own layout rules regardless of preference.

## Compare and decide (US-6)

Select each formation to compare original and proposed positions. The original marks the unavailable dancer in red. The proposal marks moved dancers with pale-purple outlines, dashed travel paths and original-position outlines. The change table includes movement distances and removed dancers. Summary metrics apply to the whole routine. The layout selector keeps the primary repair and every usable returned alternative, including alternatives for a formation other than the one currently displayed. Select the affected formation to inspect it. Metrics are recalculated from each selected proposal against the original routine. The backend currently offers alternatives for the first recognized three-column formation. Switching layouts clears the current notes and decision; previously saved decisions remain in history.

Approval and rejection apply to the entire generated proposal. Approval requires the backend's `valid` flag and consistent errors, stage, formation names/order, dancer roster, bounds, and minimum spacing. Malformed or invalid alternatives are omitted. This is geometric checking, not symmetry certification or transition/direction validation. Browser records contain the original routine, full proposal, selected absence, notes, decision, timestamp, interpreted preference, and optional AI instruction. The stored proposal includes the selected candidate label and its recalculated movement metrics. They remain after reload in the history list; a current proposal is not automatically restored. Export the current proposal and review for a portable record. Browser storage is local to this origin/profile and is not shared with the server or other captains. If storage fails, the current decision remains downloadable. Notes edited after a decision are drafts until another decision is recorded.

## Verification

```bash
node --test tests/frontend/*.test.cjs
python -m pytest -q
```

The Node checks execute the actual inline application script using a minimal DOM adapter. They cover imports, request payloads, AI success/failure and cancellation, movement tables, alternative selection, decisions, invalid results, incorrect rosters, late responses, and storage failure.

Two integration checks call the real FastAPI routes and repair algorithm through `tests/frontend/api_bridge.py`. The external Gemini function is stubbed, so tests require no credentials or billable requests. They verify real column alternatives, preference chaining, and HTTP validation errors. Run from the repository root with dependencies installed in `.venv`; the bridge uses `.venv/bin/python`. These checks do not verify browser rendering, actual HTTP transport, or a live Gemini response.

Manual browser checks:

1. Upload and confirm a PDF, then generate a repair; switch formations and confirm movement paths and table entries.
2. Approve with notes; reload and expand saved history to see the decision.
3. Replace the routine with a different PDF; check names, formation labels, stage proportions, and the grid.
4. Upload an unsupported PDF; confirm a clear error and that the previous routine remains loaded.
5. Generate then change the absent dancer; confirm the proposal and decision controls reset.
6. Reject a proposal and download its review; inspect the original, proposal, and decision in the JSON.
7. Upload and confirm Ending Bhangra, generate a repair, select each alternative, and confirm metrics and decisions follow the selected layout.
8. Select “preserve center” manually, then test an AI instruction with a configured Gemini key. With no key, confirm the error is visible and manual generation still works.
9. Use keyboard navigation and a narrow viewport to check controls and stacked diagrams.

The frontend consumes the existing response fields: routine, valid, errors, changed_assignments, total_displacement, optional note, and optional alternatives containing label, routine, and formation_index. Server and repair algorithm changes belong to the backend work. No approval API or shared persistence is introduced here.
