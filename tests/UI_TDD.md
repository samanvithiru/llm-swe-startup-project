# PDF-first UI redesign: tests before implementation

This is the **red phase**. Only tests and this guide were added. No application,
backend, frontend, dependency, or existing-test implementation was changed.
Do not implement the features or skip/mark the new acceptance tests as expected
failures before committing this snapshot. Their failures are the TDD evidence.

## New files

- `frontend/ui-redesign.test.cjs`: 8 intentionally failing acceptance checks.
- `test_pdf_grid_contract.py`: 2 intentionally failing grid metadata contracts.
- `frontend/pdf-regression.test.cjs`: 8 passing PDF-based regression checks.
- `frontend/helpers/page.cjs`: DOM adapter for the actual inline application script.

The adapter returns null for an ID missing from the HTML, like a browser. This
helps catch script references left behind when the example/demo/JSON controls
are removed. Unlike the original workflow adapter it does not invent missing
controls. Tests use no live Gemini requests or API credentials.

## Red acceptance requirements

1. Remove the example picker and Load demo routine button.
2. Remove JSON upload and JSON format/help content. Keep PDF upload and review
   downloads: removing JSON input is not a request to remove exported records.
3. Start with no loaded routine; keep repair disabled until a PDF is confirmed.
4. Use shared palette variables `--page-bg`, `--surface`, `--text`, `--accent`,
   and `--grid-line`. Exact colors remain a design choice, not a test fixture.
5. Draw PDF-aligned major grid divisions in preview, original, and repaired
   diagrams. Draw the grid behind dancers, keep it within stage boundaries,
   preserve offstage preview positions, and do not change request coordinates.
6. Preserve the PDF's grid, not just its aspect ratio. Kuthu has four depth
   divisions; Ending Bhangra has three. The additive API contract is
   `routine.stage.grid = {x: [...], y: [...]}`, where the arrays contain major
   divisions in stage units including 0 and width/height. This metadata still
   needs implementation in the importer. It is not an algorithm rewrite.

## Green regression coverage

PDF confirmation and cancellation; replacement errors; dancer names and exact
formation labels; unchanged request coordinates and preference fields; AI
preference chaining and recovery; invalid-proposal approval protection; roster
checks; candidate selection and review reset; review storage and JSON export;
stale-response protection; and real multipart import-to-repair integration.
The new safety net loads its data through the PDF workflow, never via example,
demo, or JSON import controls. Existing backend checks remain unchanged.

## Run the red tests

From the repository root with the project virtual environment activated:

```bash
node --test tests/frontend/ui-redesign.test.cjs
python -m pytest tests/test_pdf_grid_contract.py -q
```

Expected before implementation: **8 UI failures and 2 grid-contract failures**.
Check their assertion messages: they should describe missing features, not
syntax errors, missing dependencies, or HTTP connection failures.

## Run the passing safety net

```bash
node --test tests/frontend/workflow.test.cjs tests/frontend/pdf-regression.test.cjs
python -m pytest -q --ignore=tests/test_pdf_grid_contract.py
```

At creation: **29 frontend checks pass**. With both optional original-PDF paths
configured, **161 Python tests pass**. Without the PDF environment variables,
the two optional original-file regressions are skipped. No production keys are
needed. The frontend integration checks expect `.venv/bin/python` and the
existing project dependencies.

## Full suite after implementation

```bash
node --test tests/frontend/*.test.cjs
python -m pytest -q
```

Some old `workflow.test.cjs` checks explicitly exercise the demo/JSON features
being deliberately removed. During the green phase, migrate those checks to
PDF fixtures or remove only assertions about the intentionally removed features.
Do not delete unrelated regression coverage to get a green result. The new
PDF regression tests provide a starting point for that migration.

These are handler/API tests with a DOM adapter. They do not measure visual
quality, CSS contrast, actual browser layout, PDF-viewer behavior, or live Gemini
availability. Manually inspect the final palette and grid against the source PDF.
Tests reduce regression risk; they cannot guarantee that no behavior can break.

## Commit the tests-first snapshot

```bash
git add tests/frontend/helpers/page.cjs tests/frontend/pdf-regression.test.cjs tests/frontend/ui-redesign.test.cjs tests/test_pdf_grid_contract.py tests/UI_TDD.md
git commit -m "Add failing PDF-first UI acceptance tests and regression coverage"
git push origin feature/frontend
```

Application changes belong in a later commit. A failing CI run for this explicit
red-stage commit is expected; do not merge it into main until the implementation
and appropriate verification are complete.
