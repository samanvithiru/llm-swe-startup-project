# Import formations from a Sway PDF

## Run

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.server:app --reload
```

Open http://127.0.0.1:8000 and select a file with **Sway formations PDF**.

1. Export a **2D PDF with dancer names** from Sway and upload it.
2. In the import preview, select each PDF formation and check its names and positions. Use **Open original PDF page** to compare with the source.
3. Keep the formations you want checked. Pages that fail roster, boundary, or spacing checks are excluded and explain why.
4. Click **Load selected formations**. The existing routine is preserved until this confirmation.
5. Select the absent dancer and generate a repair using the existing manual or AI preference controls. PDF extraction itself does not need an AI key.

JSON import remains available under **Advanced: import routine JSON**. The downloaded routine JSON is useful for backups; captains do not need to create it manually.

## Supported export structure

The importer reads the vector structure observed in the supplied `sway-kuthu-formations.pdf`:

- One formation per page, labeled F1, F2, etc.; original order and label gaps are retained.
- A header such as `38' x 28' stage | 14 performers | 5.9s hold`.
- An outlined stage with the same aspect ratio as the stated dimensions.
- Current dancers drawn as filled circular markers with white outlines and centered text labels immediately above them.
- Faded blue previous-position markers and transition paths are ignored.

Positions are mapped relative to each page's detected stage boundary, not hardcoded page coordinates or a hardcoded list of dancer names. This matters because Sway can change the diagram scale between pages. Stage dimensions and coordinates are in feet, with x increasing rightward and y increasing downward (backstage at top, audience at bottom). Hold durations and source page numbers are retained in the imported source routine; they do not establish transition feasibility.

Upload limit: 10 MB and 80 pages. Password-protected files, scans, screenshots, 3D exports, missing labels, and other PDF layouts are not supported. Unreliable extraction fails with a page-specific error rather than guessing names or returning a partial routine. There is no automatic OCR or left/right choreography inference.

## The supplied Kuthu example

The supplied PDF contains **13 pages, 14 dancers per formation, and a 38 × 28-foot stage**. Its labels are F1, F2, F3, F5–F14; the importer does not invent F4.

F14 contains offstage exit positions, plus faded previous positions inside the stage. The importer keeps the actual exit positions and shows them in red, rather than clipping dancers to the stage or importing their ghosts. F14 is visible in preview but excluded from repair because the existing backend requires all dancers to be inside stage boundaries. The other **12 formations** are selected by default. Offstage choreography needs separate backend support before it can be repaired.

## Ending Bhangra example

The supplied `sway-70-ending-bhangra-formations.pdf` contains 12 formations with 12 dancers each. F0 is an offstage entrance: some dancers share identical positions, so their vector markers and labels overlap. The importer retains each distinct dancer at the original position and flags the geometry rather than guessing or discarding names. F0 is excluded from repair; the remaining 11 formations can be loaded. Original labels F0, F1, F2, F13–F21 are preserved.

The optional original-file regression can be run with:

```bash
SWAY_BHANGRA_PDF='/path/to/sway-70-ending-bhangra-formations.pdf' python -m pytest tests/test_pdf_import.py -q
```

## API and storage

`POST /api/import/sway-pdf` accepts a multipart field named `file`. The response contains:

- `routine`: stage dimensions and all extracted formations, including flagged offstage positions.
- `pages`: page number, formation name, dancer count, issues, and whether each formation can be loaded for repair.
- `warnings`: import limitations for the review screen.

The API parses the PDF on the application's server and does not persist it or send it to Gemini. The browser creates a temporary local file URL for the original-PDF link and releases it when the preview is replaced, cancelled, or confirmed. Existing approval records remain browser-local.

The repair algorithm has not been changed. Its minimum-spacing threshold remains 0.6 coordinate units, which means 0.6 feet for these imports. This is a geometric threshold, not a physical safety guarantee.

## Tests

```bash
python -m pytest -q
node --test tests/frontend/workflow.test.cjs
```

`tests/test_pdf_import.py` builds small synthetic vector PDFs covering names, coordinates, scaling, ghosts, offstage positions, roster changes, malformed documents, upload limits, and real import-to-repair API integration. The Node workflow tests cover preview/confirmation, selection, cancellation, errors, stale responses, and an actual multipart upload followed by repair through FastAPI's in-process client. The Gemini service remains stubbed in the frontend API bridge.

The original user PDF is not committed as a fixture. Run its optional regression locally by setting its path:

```bash
SWAY_SAMPLE_PDF='/path/to/sway-kuthu-formations.pdf' python -m pytest tests/test_pdf_import.py -q
```

Without that environment variable, only the original-file regression is skipped. Automated tests exercise extraction and application handlers; browser rendering and the browser's built-in PDF viewer still need manual review.
