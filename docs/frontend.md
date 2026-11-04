# Frontend workflow — US-1, US-2, US-6

Run from the repository root:

```bash
source .venv/bin/activate
python -m uvicorn app.server:app --reload
```

Open http://127.0.0.1:8000. No frontend build or npm dependencies are needed.

## Load and select (US-1 and US-2)

The demo loads automatically. Download its JSON to use as an import template, or upload your own routine. Every formation appears in the formation selector; the unavailable-dancer selector includes the union of dancer IDs across formations. Loading another routine or selecting another absent dancer clears the proposal and cancels pending requests.

Imports require positive finite stage dimensions, named nonempty formations, unique nonempty string IDs within each formation, and finite coordinates within the stage. Failed imports preserve the previous routine. Spacing validation remains the backend's responsibility. Frontend checks supplement the API; they do not replace server-side schema validation, which remains incomplete.

The selected absence is sent to the existing POST /api/repair endpoint as `{routine, missing}`. The client checks that the returned roster in each formation is the original roster minus that dancer before displaying the proposal.

## Compare and decide (US-6)

Select each formation to compare original and proposed positions. The original marks the unavailable dancer in red. The proposal marks moved dancers in amber with dashed travel paths and original-position outlines. The change table includes movement distances and removed dancers. Summary metrics apply to the whole routine.

Approval and rejection apply to the entire generated proposal. Approval requires the backend's `valid` flag. Browser records contain the original routine, full proposal, selected absence, notes, decision, and timestamp. They remain after reload in the history list; a current proposal is not automatically restored. Export the current proposal and review for a portable record. Browser storage is local to this origin/profile and is not shared with the server or other captains. If storage fails, the current decision remains downloadable. Notes edited after a decision are drafts until another decision is recorded.

## Verification

```bash
node --test tests/frontend/workflow.test.cjs
python -m pytest -q
```

The Node checks execute the actual inline application script using a minimal DOM adapter. They cover imports, request payloads, movement tables, decisions, invalid results, incorrect rosters, late responses, and storage failure. They do not verify browser rendering or real network integration.

Manual browser checks:

1. Generate a demo repair; switch formations and confirm movement paths and table entries.
2. Approve with notes; reload and expand saved history to see the decision.
3. Import a downloaded routine with different stage dimensions and dancer IDs; check selectors and stage proportions.
4. Upload malformed JSON or nonnumeric coordinates; confirm a clear error and that the previous routine remains loaded.
5. Generate then change the absent dancer; confirm the proposal and decision controls reset.
6. Reject a proposal and download its review; inspect the original, proposal, and decision in the JSON.
7. Use keyboard navigation and a narrow viewport to check controls and stacked diagrams.

The frontend consumes the existing response fields: routine, valid, errors, changed_assignments, total_displacement, and optional note. Server and repair algorithm changes belong to the backend work. No approval API or shared persistence is introduced here.
