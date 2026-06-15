# Karen Guard (Evaluator)

Isolated candidate evaluator. Simulates a highly skeptical Senior Technical Recruiter. Runs as a Gemini CLI (`agy`) process inside a Docker container, fully isolated from the host and from the orchestrator's context.

Karen does not know she is part of a loop. She receives a session workspace, evaluates the candidate, and writes a report.

---

## How Karen Evaluates

1. **Job vs Resume**: Reads `job.md` and `cv.md`, assesses initial alignment.
2. **Code Evidence**: Inspects cloned repositories in `repos/`, architecture, patterns, Git hygiene, test coverage.
3. **Skeptical Correlation**: Cross-references every CV claim against actual code. Flags inconsistencies and exaggerations.
4. **Report**: Writes `evaluation.md` with a structured report including a `## Technical Fit Score: N/100` line parsed by the orchestrator.

---

## Isolation Model

| Karen can see | Karen cannot see |
|---|---|
| `docs/cv.md`, `docs/job.md` | `anti_karen/` (prompt restriction) |
| `docs/who_are_u.md` (if `KAREN_READS_BACKGROUND=yes`) | Host filesystem |
| `repos/` (all cloned repositories) | Orchestrator context / previous loop state |
| `company_info.md` | Other session directories |

---

## Execution

Always run from the **repository root**:

```bash
./karen_guard/run.sh <session_id> \
  > /tmp/karen_guard_<session_id>/anti_karen/karen_run.log \
  2> /tmp/karen_guard_<session_id>/anti_karen/karen_run.err
```

> **Pre-flight**: `agy` must be authenticated before calling this command, output is fully redirected and interactive login will not work. Run `agy` interactively on the host first if credentials are missing.

---

## Output

| File | Location |
|---|---|
| Evaluation report | `SESSION_DIR/anti_karen/karen_output.md` |
| Host copy | `data/evaluation.md` |
| Stdout log | `SESSION_DIR/anti_karen/karen_run.log` |
| Stderr log | `SESSION_DIR/anti_karen/karen_run.err` |
