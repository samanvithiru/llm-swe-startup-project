# FormationRescue Alpha — executable baseline

This is an **initial working baseline**, not the finished Alpha submission. It loads six example formations of twelve dancers, removes one unavailable dancer from each, checks basic constraints, and displays before/after diagrams.

## Run

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.server:app --reload
```

Open http://127.0.0.1:8000

## Tests

```bash
python -m pytest -q
```

## Important limitations

- Removing a dancer currently leaves a vacant position; no meaningful formation reblocking is implemented yet.
- `preserve_center` is accepted but not implemented as a distinct optimization objective.
- No LLM call, artistic formation generation, transition feasibility checking, authentication, or persistent storage.
- Do not claim this prototype validates the full MVP hypothesis or demonstrates test-first development without actual evidence.

## Next engineering priorities

1. Implement a genuine formation reblocking algorithm with an explicit cost function.
2. Add direction locks, stage spacing, and movement limits; reject infeasible repairs.
3. Add real natural-language preference parsing/LLM integration and independent validation.
4. Capture genuine user trials and report sample size, time, errors, and user acceptance.
