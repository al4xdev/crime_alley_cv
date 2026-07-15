# Harvey control plane

Harvey owns the deterministic part of the actor-critic pipeline. Agent clients make judgments;
`harvey_guy.pipeline` owns state, validates artifacts and decides every transition.

## Durable state

Each run has one directory under `.runs/<run-id>/`:

```text
state.json       canonical phase, iteration, score and outcome
events.jsonl     transition journal
scores.csv       score history
iterations/      immutable inputs and outputs for each evaluation
guards/          strict Bill/Donna baselines, digests anchored in canonical state
transactions/    hashed payloads and strictly validated recoverable intent
action_plan.md    immutable copy of Donna's accepted output
logs/             boundary journal and consolidated raw process logs
sessions/         archived per-session artifacts, contracts and logs
log_tree.md       merged chronological trace and durable artifact inventory
```

Every agent session is fresh and lives under `/tmp/karen_guard_<uuid>/` by default. Harvey copies
only the current CV, job description and the explicitly configured background file into a session;
reports and draft files from older sessions are never ingested.

## Entry point

Use the module CLI from the repository root:

```fish
uv run python -m harvey_guy.pipeline --help
```

The complete sequence and the phase contracts are documented in [main.md](main.md). Callers retain
the `state_path` returned by `init` and pass it to every later command. They must not keep a second
loop counter or edit control-plane artifacts directly.

## Agent prompts

`start-session`, `prepare-bill` and `prepare-donna` render prompts from typed inputs with Jinja
`StrictUndefined`. Generated prompts live under the active session's
`anti_karen/contracts/<agent>/` directory. The
shadow agent populates repository and company evidence; Bill may change only the session CV.
Donna must replace any pre-existing action plan after `prepare-donna`; `complete-donna` archives
the accepted output inside the run before marking it complete. A digest-anchored transactional
guard also verifies that the session and canonical CV/job inputs, archived final evaluation,
session repositories and host worktree remained unchanged.

Recovery accepts only the current/next revision, the declared operation's exact target allowlist
and regular staged payloads whose size and SHA-256 match the manifest. `state.json` is unique and
last, and every copied target is hashed again before pending intent is removed. Guard snapshots
also record lexical ancestor identities and resolved paths. These checks provide crash recovery
and local corruption detection; they are not a security boundary against another same-user process.

The Fish scripts under `boundaries/` are deliberately thin adapters: each checks a phase or calls
one control-plane transition and records the handoff. `run_audit.fish --finalize STATE_PATH`
combines those records with `events.jsonl`, archives session-private evidence and produces the
final `log_tree.md`.

## Offline replay

Recorded Karen reports can exercise the complete loop without `agy`, network access or the user's
real `.data` directory:

```fish
uv run python -m tools.replay_pipeline \
    --report tests/fixtures/evaluation_72.md \
    --report tests/fixtures/evaluation_62.md \
    --report tests/fixtures/evaluation_68.md \
    --max-iterations 3 \
    --min-fit-score 80
```
