# Karen Guard: Evaluator Orchestrator Guide

This guide defines how the host orchestrator agent runs and monitors the Karen Guard (Critic) evaluation.

---

## 📥 Inputs

The orchestrator requires `SESSION_DIR` and the canonical `STATE_PATH`.

---

## 🛠️ Step-by-Step Execution & Sandboxing Rules

### 1. Run the Evaluation Command
Run the containerized evaluation wrapper script. You must redirect the output and error logs inside the isolated session folder instead of writing them directly under `/tmp/`.

The wrapper owns image refresh, authentication and runtime hardening. Do not add alternate
`docker run`/`podman run` commands in the prose orchestration: doing so would bypass its mount and
capability contract.

**Command to run:**
```fish
./karen_guard/run.sh "$SESSION_DIR" \
    > "$SESSION_DIR/anti_karen/logs/karen.stdout.log" \
    2> "$SESSION_DIR/anti_karen/logs/karen.stderr.log"
```

### 2. Monitor and Wait
- Build and CLI logs are written under `$SESSION_DIR/anti_karen/logs/`.
- The wrapper is synchronous: when it returns successfully, the evaluation has completed.
- On failure, inspect `$SESSION_DIR/anti_karen/logs/karen.stderr.log` and the other session logs.

### 3. Extract the Report and Fit Score
Once completed:
1. Treat `$SESSION_DIR/anti_karen/artifacts/karen_output.md` as the only evaluator report.
2. Do not parse the score in prose or shell. The control plane validates and records it with
   `uv run python -m harvey_guy.pipeline record-evaluation --state "$STATE_PATH"`.
