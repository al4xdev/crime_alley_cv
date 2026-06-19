# Karen Guard (Evaluator Sandbox)

Isolated candidate evaluator. Simulates a highly skeptical Senior Technical Recruiter. Runs as a Gemini CLI (`agy`) process inside a containerized sandbox, fully isolated from the host and from the orchestrator's context.

Karen does not know she is part of a loop. She receives a fresh session workspace for each evaluation, checks the candidate's claims against real evidence, and writes a report.

---

## How Karen Evaluates

1. **Job vs Resume**: Reads `job.md` and `cv.md` to assess initial alignment.
2. **Code Evidence**: Inspects cloned repositories in `repos/` (architecture, coding patterns, Git history, test coverage).
3. **Skeptical Correlation**: Cross-references every CV statement against actual code. Flags inconsistencies, hallucinations, and exaggerations.
4. **Report**: Writes `evaluation.md` containing a structured report with a `## Technical Fit Score: N/100` line parsed by the Gatekeeper.

---

## Sandboxing & Isolation Model

The evaluator implements a strict **physical isolation boundary** rather than relying solely on soft prompt instructions.

| Karen Can See | Karen Cannot See |
|---|---|
| `docs/cv.md`, `docs/job.md` | `anti_karen/` (History log, draft notes, run metrics) |
| `docs/who_are_u.md` (only if `KAREN_READS_BACKGROUND=yes`) | The host filesystem |
| `repos/` (cloned candidate repositories, mounted read-only) | Orchestrator context / past CV iterations |
| `company_info.md` (read-only research) | Other session directories |

### Isolation Mechanisms
- **Mount Hardening**: `run.sh` mounts only the specific folders `docs/`, `repos/`, and `company_info.md` as **read-only** (`:ro`). The folder `anti_karen/` is physically omitted from the volume configurations, making it structurally impossible for the evaluator to inspect execution logs or previous drafts.
- **Container Engines (Podman vs. Docker)**:
  - **Podman (Recommended / Default)**: Runs fully **rootless** inside nested container systems (using the `vfs` storage driver under Podman-in-Docker). It utilizes user namespace mapping (`--userns=keep-id`) and SELinux tags (`:z`) to prevent file access leaks to/from the host system.
  - **Docker (Fallback)**: If Podman is not installed, the runner falls back to Docker. It automatically builds the container passing host user IDs (`--build-arg USER_ID`) and executes commands inside the sandbox under that user ID (`su - <user>`), protecting root permissions.

---

## Execution

Always execute from the **repository root**:

```bash
./karen_guard/run.sh <session_id> \
  > /tmp/karen_guard_<session_id>/anti_karen/karen_run.log \
  2> /tmp/karen_guard_<session_id>/anti_karen/karen_run.err
```

> **Pre-flight**: The Antigravity CLI (`agy`) must have valid credentials. The script copies host credentials dynamically from `~/.gemini` to the session's isolated `.gemini` folder before starting. If credentials are missing, the script will halt and prompt for an interactive login flow.

---

## Output Lifecycle

Once evaluation completes, the runner moves the generated file from the writable `out/` mount into the protected `anti_karen/` folder:

| File | Location |
|---|---|
| Evaluation report | `SESSION_DIR/anti_karen/karen_output.md` |
| Host repository copy | `.data/evaluation.md` |
| Stdout runner log | `SESSION_DIR/anti_karen/karen_run.log` |
| Stderr builder log | `SESSION_DIR/anti_karen/karen_run.err` |
