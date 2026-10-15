Clever
1. Solves one problem extremely well:
It streamlines the student learning process by centralizing application access and automatically diagnosing foundational knowledge gaps during study sessions.

2. Target customers or direct access:
Study groups, teaching assistants, and student tutors.

3. Familiar infrastructure:
OAuth authentication, database schemas, API routing, and standard web backend development.

4. Reimagines the problem space:
It transforms a standard classroom login portal into an "Adaptive Prerequisite Remediation" system. If a student consistently fails quiz questions on an advanced topic (like differential equations), the system automatically traces the concept back to its mathematical prerequisite (e.g., matrix operations) and instantly generates targeted practice for that foundational skill before allowing the student to move forward.

5. LLM/Generative model is core:
The LLM is strictly required to ingest unstructured, student-uploaded lecture notes and dynamically generate customized, context-aware study quizzes.

6. Validation Guardrail:
No quiz question reaches the student without passing through a validator. A validator script parses the LLM-generated questions and cross-references them against the source material to ensure they are factually grounded and logically sound.

7. Self-Correction Loop:
If a generated question contains a logical flaw or cannot be explicitly answered using the provided notes, the validator automatically discards it and triggers the LLM to retry and generate a new question.

8. Deployability:
It can be fully deployed as a standard web application with user authentication.
