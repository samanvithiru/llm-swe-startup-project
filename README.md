# FormationRescue Alpha — executable baseline

This is an **initial working baseline**, not the finished Alpha submission. It imports named formations from supported 2D Sway PDFs, removes one unavailable dancer, checks basic geometry, and displays before/after diagrams. See [PDF import instructions](docs/pdf-import.md) to load a routine without writing JSON.

## Run

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.server:app --reload
```

Open http://127.0.0.1:8000

## Tests

```bash
python -m pytest -q
node --test tests/frontend/*.test.cjs
```

## Important limitations

- Shape-aware repair is implemented for supported patterns; other layouts use a local geometric heuristic. Whole-routine optimality is not guaranteed.
- `preserve_center` reduces center movement in the local fallback; shape-specific repairs follow their own rules.
- AI interprets instructions as a supported preference; it does not generate artistic formations. Left/right direction optimization, transition feasibility checks, authentication, and server-side routine storage are not implemented. Reviews are stored in the browser.
- Do not claim this prototype validates the full MVP hypothesis or demonstrates test-first development without actual evidence.

## Next engineering priorities

1. Implement a genuine formation reblocking algorithm with an explicit cost function.
2. Add direction locks, stage spacing, and movement limits; reject infeasible repairs.
3. Add real natural-language preference parsing/LLM integration and independent validation.
4. Capture genuine user trials and report sample size, time, errors, and user acceptance.
