# FormationRescue Alpha — user stories and acceptance criteria

## US-1 — Load a routine
As a dance captain, I want to load a multi-formation routine so that I can repair it after an absence.
- Given valid stage dimensions and formations, all formation names and dancers appear.
- Given malformed coordinates, the API returns a clear error. **Not yet implemented fully.**

## US-2 — Mark a dancer unavailable
As a dance captain, I want to select an unavailable dancer so that they are excluded from every formation.
- Given a known dancer, they are absent from every repaired formation.
- Given an unknown dancer, the repair request fails with a clear error.

## US-3 — Reblock the routine
As a dance captain, I want the remaining dancers reassigned to minimize disruption while retaining recognizable shapes.
- Output proposes meaningful position changes where needed, not just an empty spot. **Not yet implemented.**
- Output reports a defined optimization score. **Not yet implemented.**

## US-4 — Validate constraints
As a dance captain, I want automatic validation so that I can reject unusable formations.
- Out-of-bounds coordinates and spacing violations are reported.
- Unavailable dancers and duplicate dancer IDs are rejected.
- Movement and choreography-direction limits are validated. **Not yet implemented.**

## US-5 — Express artistic preferences
As a dance captain, I want to enter a plain-English preference so that the proposed repair follows it.
- Supported preference is parsed into explicit machine-readable constraints. **Not yet implemented.**
- Unsupported instructions are rejected rather than silently ignored. **Not yet implemented.**

## US-6 — Compare and approve
As a dance captain, I want side-by-side before/after formations so I can review the repair.
- Original and repaired diagrams can be compared by formation.
- Changed positions are highlighted and approval/rejection is recorded. **Not yet implemented.**

## GitHub issue workflow
Create one issue per story above, with the acceptance criteria in the issue body. Track tests, implementation, review, and validation separately. Preserve earlier-project issues as historical records rather than deleting them.
