# Harvey (Orchestrator)

Harvey is split into two parts: a deterministic Python script that sets up the session workspace, and a agent (Harvey Shadow) that performs all network and I/O-heavy tasks in parallel.

---

## Harvey Python Script (`main.py`)

The entry point for Step 1 of each loop iteration. Runs deterministically with no LLM involvement.

**What it does:**
1. Generates a unique `SESSION_ID` (UUID) and creates `/tmp/karen_guard_<UUID>/`.
2. Creates `docs/`, `repos/`, and `anti_karen/` subdirectories inside the session dir.
3. Validates that `data/docs/cv.md` and `data/docs/job.md` exist.
4. Copies all documents from `data/docs/` to `SESSION_DIR/docs/`, routing `who_are_u.md` to `anti_karen/` if `KAREN_READS_BACKGROUND=no`.
5. Checks that the `at` utility is available for the task watchdog.
6. Prints the `SESSION_ID` to stdout (captured by the orchestrator).

**Run:**
```bash
uv run python harvey_guy/main.py
```

---

## Harvey Shadow (Subagent)

Spawned by the orchestrator immediately after Harvey Python completes. Runs in parallel while the orchestrator does its concurrent CV indexing task.

**What it does:**
1. Resolves the candidate's GitHub username from `git config remote.origin.url`.
2. Fetches and clones all public repositories into `SESSION_DIR/repos/` (parallelized with `xargs -P 5`).
3. Extracts the company name from the first line of `SESSION_DIR/docs/job.md` and queries DuckDuckGo/Wikipedia for background info, saving to `SESSION_DIR/company_info.md`.
4. Pre-builds the `karen_guard` container image so it's ready when Step 2 starts.

**Runbook:** [`shadow.md`](shadow.md)

---

## Log

All execution logs are written to:
```
/tmp/karen_guard_<SESSION_ID>/anti_karen/karen_guard_core.log
```
