# Agent Architecture Guide

## Ownership model

The system is an evaluator-optimizer loop with a deterministic control plane:

| Owner | Responsibility |
|---|---|
| `harvey_guy.pipeline` | Phase, iteration count, score, session identity, artifact copies and termination |
| Harvey orchestrator | User interaction, ordered command execution and agent delegation |
| Harvey Shadow | Public repository acquisition and company research |
| Karen Guard | Evidence-based CV evaluation inside the evaluator container |
| Bill | CV revision using the validated evaluation and candidate background |
| Vera | Optional pre-run candidate background |
| Donna | Terminal action plan |

The orchestrator never owns a second counter or score. It follows the `phase` returned by the
control plane. `MAX_ITERATIONS` means the maximum number of Karen evaluations, counted from one;
there is no evaluation `MAX_ITERATIONS + 1`.

## Canonical run state

Every run lives under `.runs/<run-id>/`:

```text
state.json                 authoritative current state, atomically replaced
events.jsonl               transition evidence, atomically replaced per revision
scores.csv                 one row per completed evaluation
guards/                    Bill pre-operation integrity snapshots
transactions/              immutable staged payloads and pending recovery intent
action_plan.md              Donna output attributable to this run
iterations/<NN>/
    cv_in.md
    evaluation.md
    evaluation.json
    cv_out.md              present only when Bill revised that iteration
    draft_notes.txt        optional
```

Only `python -m harvey_guy.pipeline` may mutate `state.json`, `events.jsonl`, scores, guards or
iteration archives. Before publishing writes, it records a pending manifest whose payloads can be
reapplied safely. `state.json` is replaced last, and the next command recovers an interrupted
transition before reading state. Repeating the completed operation does not duplicate journal or
score entries.

## State machine

```text
ready
  -> shadow_running
  -> karen_ready
  -> needs_revision -> bill_running -> ready
  -> coaching_ready -> donna_running -> complete
```

`record-evaluation` is the single gate. It validates exactly one canonical
`## Technical Fit Score: N/100` line, archives the evaluated CV and report, increments the count,
then returns either `needs_revision` or `coaching_ready` with outcome `success` or
`max_iterations`.

## Session boundary

Each evaluation gets a new `SESSION_DIR` under `PIPELINE_SESSION_ROOT`:

```text
karen_guard_<uuid>/
├── docs/               cv.md, job.md and optional public who_are_u.md
├── repos/              cloned public repositories
├── company_info.md
├── out/                evaluator write target
└── anti_karen/         private and never mounted into Karen
    ├── artifacts/      report, Bill notes and optional private background
    ├── contracts/      typed prompts, instructions and JSON inputs by agent
    └── logs/           process logs and clone warnings
```

Harvey copies only the three canonical inputs. Output from a previous session is never copied into
a new one. Bill's revised CV is carried forward atomically through `.data/docs/cv.md` only after
its integrity guard passes.

Karen is the external provider boundary. Its image has a fixed non-root identity and no `sudo`;
the runner drops capabilities, enables `no-new-privileges`, mounts inputs read-only and mounts only
the selected provider credential read-only. The image contains only the selected CLI. agy uses its
sandbox, Claude denies command/edit/network tools, and Codex uses a read-only sandbox with approvals
disabled. Provider transport remains online. Never describe this as a network-disconnected
container: it is tool isolation, not a domain-level egress firewall.

## Agent contracts

Shadow, Bill and Donna receive generated `.prompt`, `_instructions.md` and `_input.json` files.
Pydantic rejects missing, extra or wrongly typed fields. Jinja uses `StrictUndefined`, so a stale
placeholder fails before the agent is spawned.

Fish scripts in `boundaries/` are audited adapters around those Python transitions. They receive
the explicit `STATE_PATH`, reject an unexpected phase and append to
`.runs/<run-id>/logs/boundary_audit.jsonl`. They never own state or use a process-global `/tmp`
audit file.

Bill's guard records types, symlink targets, absence and hashes for the report, job, company
information, both possible background locations, canonical data inputs, session inventories and
the complete cloned repository tree. It also snapshots every tracked or non-ignored host-worktree
path. The post-transition rejects any protected-context mutation before carrying the CV forward.
Donna uses the same anchored baseline pattern for both reachable CV/job copies, the archived final
evaluation, session repositories and the host worktree. Only the action plan may differ when Donna
completes.

## Runtime paths and tests

Mutable roots are deployment-owned:

| Environment variable | Default |
|---|---|
| `PIPELINE_DATA_DIR` | `.data` |
| `PIPELINE_RUNS_DIR` | `.runs` |
| `PIPELINE_SESSION_ROOT` | `/tmp` |

Pytest sets all three to a temporary root before importing application modules and refuses the
real `.data`. `tools/replay_pipeline.py` replays recorded Karen reports through the complete
control plane without an LLM call or provider quota.

## Adding an agent or phase

1. Assign one owner for its durable state and mutation.
2. Add a strict input model and template to `render_instructions.py`.
3. Add an explicit phase transition to `pipeline.py`.
4. Persist inputs, outputs and errors in the run directory.
5. Test success, invalid input, invalid phase and artifact isolation offline.
6. Add a real provider boundary test only when proportional to the risk.
