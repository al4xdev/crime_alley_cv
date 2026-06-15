# Architecture Review — Actor-Critic CV Optimization Loop
> Reviewed: 2026-06-15

---

## Executive Summary

This is a multi-agent pipeline that iteratively rewrites a CV against a scored evaluation from a real codebase audit. The high-level architecture (Actor-Critic with a Gatekeeper, filesystem-based message passing, Docker sandboxing for the critic) is sound and the isolation model is thoughtfully designed. The project has clearly gone through a round of serious bug-fixing (documented in `apontamentos.md`) that resolved most of the plumbing-level failures. The biggest risk today is not a single bug — it is that the system's correctness depends on a Claude orchestrator reliably maintaining imperative state across multiple subagent spawns and LLM-model round-trips, with no persistence mechanism beyond in-context variables. That is inherently fragile and the specs do not protect against it.

---

## Simulation Walkthrough

### Phase 0: Dependency Verification

The orchestrator spawns a Dependency Checker subagent, which reads `requirements.md` and runs a standard checklist. On completion, it writes `/tmp/dependencies_checked.md`.

**Well specified:** the dependency list is explicit and the handoff sentinel (`/tmp/dependencies_checked.md`) gives the orchestrator a clear gate.

**Vague:** the orchestrator is instructed to "verify" that file exists before proceeding, but there is no instruction on what it should do if the file is absent or contains failure status. The spec only says "wait for the subagent to complete" — it does not say "stop and report to user if the subagent reports missing dependencies." The orchestrator may proceed regardless.

**Can fail:** the subagent is spawned into a fresh context with no knowledge of the parent's conversation. The spec says "communicate directly with the user to help them install any missing tools." A subagent that talks to the user and then terminates has no way to signal the parent that the user still needs to act. The parent has no blocking mechanism — it just polls for a file.

---

### Phase 1: Interactive Setup

The orchestrator asks four questions, initializes `CURRENT_LOOP = 0`, exports `KAREN_READS_BACKGROUND`, and writes `data/docs/job.md` with a mandatory format.

**Well specified:** the `job.md` format (`# <Position Title> — <Company Name>`) is now contractually defined and Harvey Shadow's parsing logic depends on it. The `KAREN_READS_BACKGROUND` env var handoff to the Python script is explicit.

**Vague:** the orchestrator writes `data/docs/job.md` — but this is the host repository file. The SANDBOXING RULE in the same document says "do NOT modify the local repository file `data/docs/cv.md`." There is no equivalent protection for `job.md`. Overwriting the host `job.md` on every run is permanent. If the user aborts mid-run and restarts with a different job, the previous `job.md` is silently destroyed. This is inconsistent with the sandboxing philosophy.

**Can fail:** `KAREN_READS_BACKGROUND` is exported as an environment variable, but the orchestrator is a Claude LLM process — it does not actually export shell variables. The Python script reads `os.environ.get("KAREN_READS_BACKGROUND", "yes")`. If the orchestrator calls `uv run python harvey_guy/main.py` without injecting this variable via a `KAREN_READS_BACKGROUND=no uv run ...` prefix, the Python script always defaults to `"yes"`. There is no explicit instruction in Phase 1 or Step 1 telling the orchestrator to prepend the variable to the command. This is a silent correctness bug — the wrong documents get copied when the user answers "no."

---

### Loop Iteration 1 — Step 1: Harvey Python + Harvey Shadow

The orchestrator runs `uv run python harvey_guy/main.py`, captures stdout as `SESSION_ID`, derives `SESSION_DIR`, spawns Harvey Shadow with both values.

**Well specified:** the `setup_paths()` / `ingest_documents()` / `print_session_id()` chain is deterministic and clean. The Python code is correct. The Shadow's step-by-step plan is explicit enough for a subagent to follow.

**Vague:** the instruction "Concurrent Task while Subagent runs: Inspect the temporary session CV file" has no definition of what "index the technologies" means or what the orchestrator is supposed to do with that information. It appears to be dead spec — a placeholder idea that never got operationalized. It adds noise.

**Can fail (critical):** Harvey Shadow clones all public repos with `xargs -P 5`. For a GitHub user with 30+ repos this is a multi-minute operation that happens on every loop iteration. The shadow runbook does not skip repos that were already cloned in a previous iteration (the session UUID changes each iteration, so it always starts from scratch). This means Iteration 2 clones everything again from zero. No caching, no incremental update. For a large public GitHub profile this will be slow and will hit GitHub's unauthenticated rate limit (60 req/hour). The pipeline will silently get truncated clone lists or fail clones after iteration 1.

**Can fail (moderate):** the company research step (Step 3 of Shadow) uses DuckDuckGo's instant answer API (`/api.duckduckgo.com/?q=...&format=json`) which does not reliably return content for arbitrary company names. For obscure companies or Brazilian companies without English Wikipedia articles, `company_info.md` will be written but essentially empty. Karen's prompt never reads `company_info.md` — it is not mounted into the Docker container or referenced in `prompt_persona.txt`. The research output is orphaned. No agent consumes it.

---

### Loop Iteration 1 — Step 2: Karen Guard

`run.sh SESSION_ID` is called, stdout and stderr are redirected to log files. Karen runs inside Docker with the session directory mounted. She reads `docs/cv.md`, `docs/job.md`, and `repos/`, then writes `evaluation.md`. `run.sh` moves it to `anti_karen/karen_output.md` and prints the path on stdout.

**Well specified:** the Docker isolation model is correct and the file handoff is clean. The FIT_SCORE format (`## Technical Fit Score: <number>/100`) is explicit and parseable. The `run.sh` fallback build (if Shadow's pre-build failed) is a good defensive pattern.

**Vague:** Karen's prompt instructs her to write `evaluation.md` to the working directory (`cd /app/session`). The run script checks for `${SESSION_DIR}/evaluation.md` on the host. This relies on the Docker volume mount correctly aliasing `/app/session` to `SESSION_DIR`. This is correct as currently specified, but the mapping is only visible by reading both `run.sh` and `run_evaluator.sh` together — it is not stated in `karen_guard/main.md`. A future maintainer modifying the mount path would break the file handoff silently.

**Can fail:** `run.sh` checks auth by running `agy models` inside Docker and grepping for "Error|Authentication|sign in". If the auth check returns unexpected output (e.g., a deprecation warning, rate limit message, or network timeout that does not match the grep pattern), the script proceeds to run the full evaluation against an unauthenticated Gemini session and produces no `evaluation.md`, failing only at the end. The fallback "interactive login" flow (`docker run -it`) cannot work when the orchestrator has already redirected stdout/stderr to files — the TTY will not be attached. The `agy` authentication problem is a hard blocker that can only be diagnosed after the fact by reading the error log.

---

### Loop Iteration 1 — Gatekeeper

The orchestrator reads `KAREN_REPORT_PATH` (from the last line of `karen_run.log`), opens the file, and extracts `FIT_SCORE` by pattern-matching the "Technical Fit Score" section.

**Can fail (hard):** `karen_run.log` contains the output of `run.sh` stdout. The last line is printed by the final `echo` in `run.sh` — but only if all prior steps succeed. If Karen's evaluation ran partially and `evaluation.md` was written with a different section heading (Gemini models sometimes alter formatting slightly), the `run.sh` success path prints the path but the orchestrator's regex for `## Technical Fit Score: <N>/100` finds nothing. `FIT_SCORE` is undefined. The orchestrator is given no fallback instruction — it may loop indefinitely with a null score, or it may exit prematurely by interpreting an empty value as 0.

**Vague:** the Gatekeeper exit condition is `FIT_SCORE >= MIN_FIT_SCORE OR CURRENT_LOOP >= MAX_LOOPS`. The "exit" action is "copy the final CV back to the repo." There is no instruction to notify the user of the final score, explain why the loop ended, or produce a summary report. The pipeline ends silently.

---

### Loop Iteration 2: Session Reuse vs. Fresh Session

On the second loop, the orchestrator calls `uv run python harvey_guy/main.py` again. The Python script always generates a new `uuid.uuid4()`. This means:

- A brand-new `SESSION_DIR` is created under `/tmp/`.
- Harvey Shadow re-clones all repositories into the new directory.
- Bill's revision from Iteration 1 (written to the old `SESSION_DIR/docs/cv.md`) is **lost**.

The orchestrator then instructs Harvey Shadow to use the new `SESSION_ID`. But the revised CV from Iteration 1 is at the old path. There is no instruction in Step 1 or the Shadow runbook to carry forward the CV from the previous session. The runbook says: "Inspect the temporary session CV file `/tmp/karen_guard_$SESSION_ID/docs/cv.md` (if already created by a previous loop run) **or** index the local file `data/docs/cv.md` on the first iteration." This instruction is contradictory — if SESSION_ID changes each iteration, the previous iteration's CV is at a different path, not the current `SESSION_ID` path.

The practical outcome: **Karen evaluates the original, unmodified `data/docs/cv.md` on every iteration**, because that is what `ingest_documents()` copies. Bill's work is never fed back into the next Karen evaluation. The feedback loop is broken by design.

---

### Exit: CV Return to Repo

On exit, the orchestrator copies `/tmp/karen_guard_$SESSION_ID/docs/cv.md` to `data/docs/cv.md`. Since Bill's edits (if they happened at all) are in the same-session `SESSION_DIR`, the copy is correct for a single-iteration run. For multi-iteration runs, see above — the final copied CV is the Iteration N revision, but Iterations 1 through N-1 fed unrevised CVs to Karen.

---

## Architecture Strengths

- **Isolation model is coherent.** Docker for Karen, `anti_karen/` directory for Bill's scratchpad, file-based message passing with no shared memory — the boundaries are well-enforced and the reasoning behind each constraint is documented.
- **`run.sh` defensive patterns.** The `sg docker` fallback, the pre-built image skip, the GID fix, the missing-file `exit 1` — these are real operational improvements that would have caused silent failures in production.
- **`who_are_u.md` routing logic.** The `KAREN_READS_BACKGROUND` flag and the two-path routing (`session/docs/` vs `anti_karen/`) for the background file is a genuine piece of domain-specific safety: it prevents Karen from scoring against non-public information while allowing Bill to use it for honest editing.
- **Bill's anti-hallucination constraints.** The `who_are_u.md` as ground truth, the NDA clause, the "no invented certifications" rule — these are operationally important for the real use case and are explicitly specified.
- **`apontamentos.md` as a living bug log.** The decision to document every fix with before/after rationale creates an accurate audit trail and prevents regressions from being re-introduced silently.

---

## Critical Gaps

**1. Session UUID regeneration breaks the feedback loop (severity: fatal)**
Every call to `uv run python harvey_guy/main.py` produces a new UUID and a new empty session directory. The revised CV from iteration N lives at `/tmp/karen_guard_<UUID_N>/docs/cv.md`. The Harvey Python script in iteration N+1 copies from `data/docs/cv.md` — which is the original, unedited CV. Bill's revision is never passed forward. The loop has no memory. This must be fixed: either the Python script accepts an optional previous `SESSION_DIR` argument and copies the revised CV forward, or the orchestrator explicitly copies `SESSION_DIR_N/docs/cv.md` to `data/docs/cv.md` after each Bill revision before calling Harvey again.

**2. `KAREN_READS_BACKGROUND` env var is never injected into the subprocess (severity: high)**
The orchestrator stores the user's answer as an in-context variable but has no instruction to prepend it to the `uv run` command. The Python script defaults to `"yes"`. When the user answers "no," `who_are_u.md` is copied to `session/docs/` instead of `anti_karen/` — making Karen read the background file she was supposed to be blind to. The fix is trivial (one line in the runbook), but the bug is silent.

**3. `company_info.md` is never consumed by any agent (severity: moderate)**
Harvey Shadow spends time researching the company and writing `company_info.md` to `SESSION_DIR`. Karen's prompt does not reference it. The Docker container mounts `SESSION_DIR` as `/app/session`, so the file is accessible — but Karen's instructions make no mention of reading `company_info.md`. This is dead work. Either add an instruction to Karen's prompt to read it, or remove the research step from Shadow.

**4. GitHub rate limiting with no authentication (severity: moderate)**
Shadow clones repos via the unauthenticated GitHub API (60 requests/hour). A profile with 60+ repos on the first call plus partial retries on subsequent iterations will hit the limit mid-clone with no retry logic or error handling. The clone step uses `xargs -P 5` background processes — failures from individual `git clone` calls are not checked. The orchestrator verifies that `SESSION_DIR/repos/` "is populated" but has no way to know if 10 of 30 repos silently failed to clone.

**5. FIT_SCORE extraction has no fallback (severity: moderate)**
The orchestrator is told to "locate the Technical Fit Score section and extract the numeric value." If Gemini reformats the heading, uses different capitalization, outputs it as plain text rather than a Markdown heading, or generates no score at all (which happens on model refusals or truncated outputs), `FIT_SCORE` is undefined. The gatekeeper logic does not specify what to do with a null or unparseable score.

---

## Design Concerns

**Orchestrator state is ephemeral by design with no checkpoint mechanism.** `CURRENT_LOOP`, `FIT_SCORE`, `SESSION_ID`, and `KAREN_REPORT_PATH` exist only in the orchestrator's context window. A context reset, a token limit, or a simple model error mid-loop loses all state. There is no instruction to write these variables to a file at the start of each iteration for recovery. For a pipeline that can run 3-5 Claude subagents and a Docker process per iteration, this is a real operational risk.

**The "line-by-line sequential execution" instruction is not enforceable.** `main.md` instructs the orchestrator to "read and execute in strict sequential, line-by-line order" and "do NOT read the entire file at once." This is a prompt preference, not a constraint. The LLM reads the entire file into context on load. The instruction creates an expectation of step-gating that the architecture cannot technically guarantee — particularly for long runbooks where the model may attempt to batch steps.

**Karen's isolation is enforced by prompt instruction, not by filesystem permissions.** The `anti_karen/` folder sits inside the same Docker volume mount as `docs/` and `repos/`. There is no `chmod`, `chroot`, or mount restriction that prevents Karen from reading it. The security boundary is `"You MUST NOT read... any files or folders contained within the anti_karen/ directory"` in `prompt_persona.txt`. This is soft enforcement. A misbehaving or jailbroken evaluation could trivially read Bill's draft notes or the candidate's private background if Karen was ever accessed adversarially.

**Harvey Shadow's Docker pre-build provides no benefit across iterations.** The pre-build in Shadow step 4 saves time on the first Karen run. But since Shadow runs on every loop iteration with a new session UUID and new session directory, it rebuilds the image every time — then `run.sh`'s `docker image inspect` guard correctly skips the rebuild. The pre-build adds latency to each Shadow execution (a full Docker build) for zero benefit after the first run. It should only be triggered if the image does not already exist.

**`billf/main.md` hardcodes the headline "GenAI Platform Engineer."** This is a specific personal preference embedded in a general-purpose architecture. The CV editor is instructed to always set the headline to "GenAI Platform Engineer" regardless of the target job description. If the user runs this against a backend engineering role, a data engineering role, or any position where that headline is a mismatch, Bill will still override the headline. This should be a user configuration variable, not a hardcoded instruction.

---

## Verdict

The pipeline is not ready for a first real execution. The architecture is viable and the isolation model is correct, but there is one fatal design flaw that makes the core feedback loop inoperative: because Harvey's Python script generates a new session UUID on every call, Bill's revision is written to a directory that Harvey's next iteration never reads from. Karen evaluates the original CV on every loop, Bill rewrites it every time, and nothing converges. This alone disqualifies a multi-iteration run. The fix is a single engineering decision — either pass the previous session's CV forward explicitly or have the orchestrator copy it back to `data/docs/cv.md` after each Bill revision before the next Harvey call. Until that is resolved, running with `MAX_LOOPS > 1` produces wasted compute and gives the user a false signal that the system is optimizing when it is not.
