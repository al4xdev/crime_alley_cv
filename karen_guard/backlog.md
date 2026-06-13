# Karen Guard — Backlog

> Planned features for the isolated evaluation environment.
> This file is the specific planning for the Karen Guard module.

---

## Upcoming Deliveries

### 3. evaluator.py — Stateless Evaluator
- [ ] Develop evaluation script based on the Gemini/Claude SDK.
- [ ] Load the senior technical recruiter persona from a prompt file.
- [ ] Read the CV and repository files from the mounted volume.
- [ ] Return the structured evaluation report (`evaluation.md`).

---

## Out of Scope (Simplified)

- **CV Anonymization**: Removed. Evaluation will be conducted using the direct CV, since a clean API session already guarantees isolation against historical data.
- **Local Credentials Mapping (gcloud config mount)**: Will not be performed unless strictly necessary. We will use standard environment variables (`GEMINI_API_KEY`) for stateless API authentication.
