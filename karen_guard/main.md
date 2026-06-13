# Karen Guard: Evaluator Orchestrator Guide

This guide defines how the host orchestrator agent runs and monitors the Karen Guard (Critic) evaluation.

---

## 📥 Inputs

The orchestrator requires:
- **`SESSION_ID`**: The active session UUID (e.g., `8ec80956-9f61-47d8-9a07-3942ffb87d7c`).

---

## 🛠️ Step-by-Step Execution & Sandboxing Rules

### 1. Run the Evaluation Command
Run the Docker evaluation wrapper script. You must redirect the output and error logs inside the isolated session folder instead of writing them directly under `/tmp/`.

**Command to run:**
```bash
./karen_guard/run.sh $SESSION_ID > /tmp/karen_guard_$SESSION_ID/karen_run.log 2> /tmp/karen_guard_$SESSION_ID/karen_run.err
```

### 2. Monitor and Wait
- The Docker image build and CLI execution logs will be written to `/tmp/karen_guard_$SESSION_ID/karen_run.err` (stderr) and `/tmp/karen_guard_$SESSION_ID/karen_run.log` (stdout).
- Read `/tmp/karen_guard_$SESSION_ID/karen_run.err` to check building progress and verify if Antigravity CLI has successfully started the evaluation process inside the container.
- Wait for the background process to complete.

### 3. Extract the Report and Fit Score
Once completed:
1. Read the last line of `/tmp/karen_guard_$SESSION_ID/karen_run.log` to retrieve the absolute path to the generated evaluation report. This is **`KAREN_REPORT_PATH`** (typically `/tmp/karen_guard_$SESSION_ID/karen_output.md`).
2. Open **`KAREN_REPORT_PATH`** (or the host copy at [data/evaluation.md](file:///home/alex/git/my/meta_2028/data/evaluation.md)).
3. Locate the **"Technical Fit Score"** section (e.g., `## Technical Fit Score: 75/100`) and extract the numeric value as **`FIT_SCORE`**.
