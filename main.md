# Execution Runbook: Actor-Critic CV Optimization Loop

Welcome, Agent! You are entering a multi-agent loop designed to refine a candidate's CV against a job description. 
Read this runbook sequentially. You must initialize state variables, run tasks in parallel where instructed, and execute the feedback loop until the acceptance criteria are met.

---

## 🤖 Global Agent Execution Rules

To ensure reliable, safe, and consistent execution on the host machine, you must strictly adhere to the following rules:

### 1. Shell & Tooling
- **Shell**: Use the system's default shell (e.g., bash/sh) or the user's preferred shell, ensuring commands are compatible.
- **Python projects**: Use `uv` with virtual environment at `.venv/`, activated via `source .venv/bin/activate` (or `activate.fish` if using fish).
- **Display Server**: Use the available display server. If Wayland is active, pipe terminal outputs to `wl-copy` when sharing content for the user.
- **Command Output Capture**: Every shell command must capture output. Never run a command and assume it succeeded. Always check exit codes or append appropriate error-handling checks compatible with the shell being used.
- **Silent Commands**: For commands with no natural output (e.g., `mv`, `mkdir`, `chmod`, `git add`), verify success by appending success indicators (like `&& echo ok` or equivalent).

### 2. Long-Running Task Watchdog
- Before starting any task expected to take >30 seconds, register it:
  `echo (date +%s) $task_description > /tmp/agt_task_active`
- On completion (success or failure), clear it:
  `rm -f /tmp/agt_task_active`
- If a sub-agent or background process is spawned, set a cron to alert if still running after 5 minutes:
  `echo "notify-send 'AGY watchdog' 'Task may be stuck: $task_description'" | at now + 5 minutes`
- If `/tmp/agt_task_active` already exists when starting a new task, report it immediately to the user.

### 3. Execution Style & Scope Discipline
- **Persona**: Direct, no filler. Act like a senior staff engineer.
- **Root Cause First**: Do not patch symptoms. Check for edge cases and security risks before touching anything.
- **Anti-Looping**: If you run the same command or hit the same error twice, **stop**. Analyze why it failed, form a new hypothesis, verify assumptions, then act. If stuck, explain what failed and ask for direction.
- **Scope Discipline**: Do not add features, refactor, or abstract beyond the task. Report failures and skipped steps faithfully.
- **Code Discipline**: No placeholders (`// ... rest of code`). Always write complete code. Read a file before editing it. Check linter output after every change.
- **Language Selection**: Default to shell scripts (bash/sh/fish) + standard Unix tools (`jq`, `awk`, `sed`, `curl`, `fd`, `rg`) for system tasks. Only use Python when libraries have no shell equivalent or logic is genuinely clearer in Python. State why in one sentence before writing Python.
- **Destructive File Ops**: Move files to `/tmp/` (or `.bak`) instead of `rm -rf`. Use plain `rm` only when the user explicitly says "delete", "rm", or "permanently remove".

---

## 🎮 Phase 0: Initialize State (Interactive Setup)

Before executing any commands, you must enter "interactive setup mode". Ask the user the following questions to initialize the loop configuration variables (always reference them in **UPPERCASE**):

1. **`MAX_LOOPS`**: What is the maximum number of CV refinement iterations allowed? (e.g., `3`)
2. **`MIN_FIT_SCORE`**: What is the target minimum technical fit score (0-100) needed to accept the CV? (e.g., `80`)
3. **`JOB_DESCRIPTION_RAW`**: Please paste the raw text of the target job description.
4. **`DEPENDENCY_CHECK_AT`**: Verify if the `at` command-line utility is installed (e.g., run `which at` or `at -V`). If it is not found, instruct the user to install it (e.g., `sudo apt install at` on Debian/Ubuntu, `brew install at` on macOS, or equivalent) and confirm before proceeding.

### Initialization Actions:
- Initialize **`CURRENT_LOOP`** to `0`.
- Verify the presence of the `at` utility. If missing, block and ask the user to install it.
- Write/update the parsed job description to [data/docs/job.md](file:///home/alex/git/my/meta_2028/data/docs/job.md) based on the **`JOB_DESCRIPTION_RAW`** input.

> [!IMPORTANT]
> **SANDBOXING RULE**: During the loop iterations, do NOT modify the local repository file `data/docs/cv.md`. All updates and edits must occur exclusively inside the session directory at `/tmp/karen_guard_$SESSION_ID/docs/cv.md`.

---

## 🔁 The Optimization Loop (Play Phase)

Execute the following steps inside a loop. The loop continues while **`CURRENT_LOOP`** < **`MAX_LOOPS`** AND the latest **`FIT_SCORE`** < **`MIN_FIT_SCORE`**.

```mermaid
graph TD
    Start([Start Loop]) --> Step1[Step 1: Harvey - Parallel Ingestion]
    Step1 --> Step2[Step 2: Karen - Skeptical Audit]
    Step2 --> Check{Gatekeeper Check}
    Check -- "FIT_SCORE >= MIN_FIT_SCORE" --> End([Exit Loop - Success])
    Check -- "CURRENT_LOOP >= MAX_LOOPS" --> End
    Check -- "Refine CV" --> Step3[Step 3: Bill - Delegate Revision]
    Step3 --> Increment[Increment CURRENT_LOOP]
    Increment --> Step1
```

---

### Step 1: Parallel Context Preparation (Harvey)

Execute Harvey's main entrypoint to setup the directory layout, ingest docs, clone repositories, and research the target company.

**Command to run:**
```bash
uv run python harvey_guy/main.py
```

**⚡ Parallel Execution Instruction for the Agent:**
While the above command is running (which clones repositories and queries APIs), you should spin up a parallel thread or run commands concurrently to:
1. **Parallel Task A**: Monitor the progress of repository clones inside `/tmp/karen_guard_$SESSION_ID/repos/`.
2. **Parallel Task B**: Inspect the temporary session CV file `/tmp/karen_guard_$SESSION_ID/docs/cv.md` (if already created by a previous loop run) or index the local file [data/docs/cv.md](file:///home/alex/git/my/meta_2028/data/docs/cv.md) on the first iteration to map technologies.

**Actions:**
1. Execute the main pipeline command.
2. Capture the `stdout` session UUID, and store it as **`SESSION_ID`**.
3. Verify that `/tmp/karen_guard_$SESSION_ID/company_info.md` and the protected folder `/tmp/karen_guard_$SESSION_ID/anti_karen/` are created successfully.

---

### Step 2: Skeptical Auditing (Karen Guard)

Delegate or follow the instructions defined in [karen_guard/main.md](file:///home/alex/git/my/meta_2028/karen_guard/main.md) to execute the evaluator docker sandbox using the active **`SESSION_ID`**.

**Command to run:**
```bash
./karen_guard/run.sh $SESSION_ID > /tmp/karen_guard_$SESSION_ID/karen_run.log 2> /tmp/karen_guard_$SESSION_ID/karen_run.err
```

**Actions:**
1. Execute the command above to isolate output logs inside the session directory.
2. Monitor progress by viewing `/tmp/karen_guard_$SESSION_ID/karen_run.err`.
3. Retrieve **`KAREN_REPORT_PATH`** from the last line of `/tmp/karen_guard_$SESSION_ID/karen_run.log`.
4. Open **`KAREN_REPORT_PATH`** (or the host copy [data/evaluation.md](file:///home/alex/git/my/meta_2028/data/evaluation.md)) and extract the **`FIT_SCORE`** (parsed from the "Technical Fit Score" section).

---

### 🛑 The Gatekeeper (Evaluation & Termination Check)

Compare your variables:
- **IF** **`FIT_SCORE`** >= **`MIN_FIT_SCORE`**:
  - **Exit Loop**: The CV has successfully met the user's requirements. Copy the final optimized CV from `/tmp/karen_guard_$SESSION_ID/docs/cv.md` back to the local repository at [data/docs/cv.md](file:///home/alex/git/my/meta_2028/data/docs/cv.md).
- **IF** **`CURRENT_LOOP`** >= **`MAX_LOOPS`**:
  - **Exit Loop**: Reached maximum cycles. Copy the last iteration's CV from `/tmp/karen_guard_$SESSION_ID/docs/cv.md` back to the local repository at [data/docs/cv.md](file:///home/alex/git/my/meta_2028/data/docs/cv.md) and report the final status.
- **ELSE**:
  - Proceed to **Step 3 (Bill)**.

---

### Step 3: CV Revision (Bill)

Delegate the CV revision to a specialized subagent. This isolates the editing logic and prevents cluttering the main orchestrator's context.

**Actions:**
1. Spawn a subagent (Bill) to optimize the CV.
2. Instruct the subagent to read and execute the instructions defined in [billf/main.md](file:///home/alex/git/my/meta_2028/billf/main.md) using the active **`SESSION_ID`** and **`KAREN_REPORT_PATH`**.
3. Wait for the subagent to complete the revision. (The subagent will modify `/tmp/karen_guard_$SESSION_ID/docs/cv.md` directly).
4. Increment **`CURRENT_LOOP`** by 1.
5. Restart the loop from **Step 1**.
