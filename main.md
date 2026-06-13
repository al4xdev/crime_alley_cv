# Execution Runbook

This document defines the step-by-step execution plan for running the Job-Stack & Karen Guard multi-agent pipeline. Any clean-slate agent can read this runbook to orchestrate the entire process on the user's system.

## Pipeline Overview

The pipeline executes three main agents in sequence:
1. **Harvey (Orchestrator)**: Gathers data and maps repositories.
2. **Karen Guard (Evaluator/Critic)**: Analyzes CV against the job description and repository code quality, generating a defect report.
3. **Bob Revisor (Editor/Generator)**: Revises the candidate's CV based on Karen's defect report.

---

## Step-by-Step Execution Plan

### Step 1: Run the Orchestrator (Harvey)

Execute Harvey's main entrypoint. This sets up the directory layout, copies local documents, clones public repositories to the session folder, and outputs the unique session UUID.

**Command to run:**
```bash
uv run python harvey_guy/main.py
```

**Action for the Agent:**
1. Execute the command above.
2. Capture the standard output (`stdout`), which is a single line containing the session UUID (e.g., `0e4a5edd-140d-4ba1-9378-3bc4c5791507`).
3. Store this UUID as `SESSION_ID`. The session directory on the host will be `/tmp/karen_guard_$SESSION_ID/`.

---

### Step 2: Run the Evaluator (Karen Guard)

Run the evaluation environment. This boots the Docker container, starts `agy` inside the sandbox to analyze the CV and cloned repositories, and generates a critical review.

**Command to run:**
```bash
./karen_guard/run.sh <SESSION_ID>
```
*(Replace `<SESSION_ID>` with the UUID captured in Step 1).*

**Action for the Agent:**
1. Execute the command above.
2. This runs interactively. Once complete, `run.sh` will print the absolute path of the generated evaluation report on `stdout` (e.g., `/tmp/karen_guard_<SESSION_ID>/karen_output.md`).
3. Capture this path as `KAREN_REPORT_PATH`. A copy of the report is also saved locally at `data/evaluation.md`.

---

### Step 3: Run the CV Editor (Bob Revisor)

*Note: This step is under planning and will be updated as Bob's entrypoint is implemented.*

Once Bob's revisor pipeline is set up, run Bob's script to rewrite the candidate's CV using Karen's report:

**Command to run:**
```bash
# Planned execution command:
# ./bob_revisor/run.sh <SESSION_ID> <KAREN_REPORT_PATH>
```
This will produce the final polished CV inside the `data/` directory.
