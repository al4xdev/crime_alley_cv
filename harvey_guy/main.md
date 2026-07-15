# Execution Runbook: Actor-Critic CV Optimization Loop

This runbook delegates judgment to agents and delegates every state transition to
`harvey_guy.pipeline`. Never keep a second loop counter or copy pipeline artifacts manually.

## Global rules

- Execute phases sequentially and stop on any non-zero command.
- Use fish syntax for shell commands.
- `state.json` is the only source of truth for phase, iteration, score, session and outcome.
- Agent prompts are generated inside the active session from validated contracts.
- Do not edit `.runs/<run-id>/state.json`, `events.jsonl` or guard files manually.

## Phase 0: verify the host

Read [requirements.md](../requirements.md) and verify Python, `uv`, a supported container engine,
Git and `jq`. Do not create a persistent “dependencies checked” marker: dependencies can change
between runs.

## Phase 1: collect inputs

Collect these values in one interaction:

1. `MAX_ITERATIONS`: maximum number of Karen evaluations. Suggested default: `3`.
2. `MIN_FIT_SCORE`: target score from 0 through 100. Suggested default: `80`.
3. `JOB_DESCRIPTION_RAW`: complete target job description.
4. `KAREN_READS_BACKGROUND`: `yes` or `no`.

Resolve the configurable data directory before writing any host input:

```fish
set DATA_DIR .data
if set -q PIPELINE_DATA_DIR
    set DATA_DIR "$PIPELINE_DATA_DIR"
end
mkdir -p "$DATA_DIR/docs"
or return 1
```

Write `$DATA_DIR/docs/job.md` in this exact format:

```markdown
# <Position> — <Company>

<JOB_DESCRIPTION_RAW>
```

Ensure `$DATA_DIR/docs/cv.md` exists. If `$DATA_DIR/docs/who_are_u.md` is absent, offer to run Vera from
[vera_psyco/main.md](../vera_psyco/main.md) before initializing the run and provide its absolute
path as `BACKGROUND_PATH`.

Initialize the canonical run and retain only `STATE_PATH`:

```fish
set init_json (uv run python -m harvey_guy.pipeline init \
    --max-iterations "$MAX_ITERATIONS" \
    --min-fit-score "$MIN_FIT_SCORE" \
    --karen-reads-background "$KAREN_READS_BACKGROUND" | string collect)
or return 1
set STATE_PATH (echo "$init_json" | jq -r .state_path)
test -f "$STATE_PATH"
or return 1
./boundaries/run_audit.fish --init "$STATE_PATH"
or return 1
```

## Optimization loop

Repeat the following sequence only while the control plane returns `phase=ready`.

### 1. Start a fresh session

```fish
./boundaries/harvey_setup.fish --pre "$STATE_PATH" >/dev/null
or return 1
set session_json (./boundaries/harvey_setup.fish --post "$STATE_PATH" | string collect)
or return 1
set SESSION_ID (echo "$session_json" | jq -r .current_session_id)
set SESSION_DIR (echo "$session_json" | jq -r .current_session_dir)
```

```fish
./boundaries/harvey_shadow.fish --pre "$STATE_PATH" >/dev/null
or return 1
```

Spawn Harvey Shadow and instruct it to execute
`$SESSION_DIR/anti_karen/contracts/shadow/shadow.prompt`. Wait for
completion, then validate and commit its output:

```fish
./boundaries/harvey_shadow.fish --post "$STATE_PATH"
or return 1
```

### 2. Run Karen

```fish
./boundaries/harvey_karen.fish --pre "$STATE_PATH" >/dev/null
or return 1
./karen_guard/run.sh "$SESSION_DIR" \
    > "$SESSION_DIR/anti_karen/logs/karen.stdout.log" \
    2> "$SESSION_DIR/anti_karen/logs/karen.stderr.log"
or return 1
```

Record the evaluation. This command validates the canonical score, then atomically archives the
iteration, publishes the validated evaluation convenience copy under the configured data directory, increments the
authoritative count and decides whether to revise or finish:

```fish
./boundaries/karen_gatekeeper.fish --pre "$STATE_PATH" >/dev/null
or return 1
set evaluation_json (./boundaries/harvey_karen.fish --post "$STATE_PATH" | string collect)
or return 1
./boundaries/karen_gatekeeper.fish --post "$STATE_PATH" >/dev/null
or return 1
set PHASE (echo "$evaluation_json" | jq -r .phase)
set FIT_SCORE (echo "$evaluation_json" | jq -r .latest_score)
```

### 3. Branch on the returned phase

If `PHASE` is `needs_revision`:

```fish
set bill_json (./boundaries/gatekeeper_bill.fish --pre "$STATE_PATH" | string collect)
or return 1
```

Spawn Bill and instruct it to execute `$SESSION_DIR/anti_karen/contracts/bill/bill.prompt`. Wait
for completion, verify the active guard, then atomically validate and commit the revision:

```fish
./boundaries/gatekeeper_bill.fish --post "$STATE_PATH" >/dev/null
or return 1
./boundaries/bill_harvey.fish --pre "$STATE_PATH" >/dev/null
or return 1
./boundaries/bill_harvey.fish --post "$STATE_PATH"
or return 1
```

Restart at “Start a fresh session”. Do not increment any variable manually.

If `PHASE` is `coaching_ready`, leave the loop. Any other phase is an error.

## Post-loop coaching

Read the terminal `outcome` (`success` or `max_iterations`) from the last JSON result. Prepare
Donna:

```fish
./boundaries/gatekeeper_donna.fish --pre "$STATE_PATH"
or return 1
```

Spawn Donna and instruct it to execute `$SESSION_DIR/anti_karen/contracts/donna/donna.prompt`. It
must write the `ACTION_PLAN_PATH` named in that validated contract. Then finish the run:

```fish
set final_json (./boundaries/gatekeeper_donna.fish --post "$STATE_PATH" | string collect)
or return 1
echo "$final_json" | jq .
./boundaries/run_audit.fish --finalize "$STATE_PATH"
or return 1
```

The run is complete only when `phase` is `complete`. All durable evidence is under the `run_dir`
reported in the JSON: canonical state, immutable-prefix event history, score history,
per-iteration inputs and outputs, archived session evidence, `logs/pipeline.log` and the final
`log_tree.md`.
