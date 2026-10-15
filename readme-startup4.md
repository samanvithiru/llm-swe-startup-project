Melder
1. Solves one problem extremely well: It simplifies spreadsheet analysis while solving the specific problem of inconsistent formulas, incorrect cell references, and calculation errors in complex spreadsheets.

2. Target customers or direct access: College students, researchers, data analysts, small businesses, and student organization boards that rely on spreadsheets to track data, budgets, research results, or project progress.

3. Familiar infrastructure: CSV and Excel parsing, Python (Pandas), spreadsheet formula evaluation, data validation, and basic web backend development.

4. Reimagines the problem space: It transforms a standard AI spreadsheet assistant into an AI Spreadsheet Formula Consistency Checker. As users upload or edit spreadsheets, the system analyzes formulas across rows and columns, detects inconsistent calculations, and flags suspicious cell references or unexpected values. For example, if one row calculates a total using the wrong cell reference, the system identifies the inconsistency and suggests the expected formula.

5. LLM/Generative model is core: The LLM is essential for interpreting spreadsheet structure, explaining potential errors in natural language, and recommending corrections based on surrounding formulas, column labels, and data patterns. It helps users understand not only what might be wrong but also why the issue matters.

6. Validation Guardrail: No suggested correction is accepted without validation. The validator independently recalculates supported formulas, compares formulas across similar rows, and checks proposed results against the spreadsheet's underlying data. It flags uncertain cases rather than treating every AI suggestion as correct.

7. Self-Correction Loop: If the validator detects an incorrect formula, an invalid cell reference, or a mismatch between the suggested correction and the expected result, it feeds the specific error back to the LLM. The LLM generates a revised suggestion, which is checked again before being presented to the user.

8. Deployability: It can be deployed as a web-based spreadsheet analysis tool using a frontend framework such as React, a Python backend, Pandas for data processing, and an LLM API. For a six-week MVP, users could upload CSV or Excel files, view flagged inconsistencies, and review validated correction suggestions without requiring a full spreadsheet editor.
