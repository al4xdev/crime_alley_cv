# Karen Guard evaluator

Karen evaluates one fresh session and writes a report with exactly one canonical score line:

```markdown
## Technical Fit Score: N/100
```

The deterministic parser accepts only an integer from 0 through 100 in that form. The pipeline
archives the report, increments its authoritative iteration count and chooses either
`needs_revision` or `coaching_ready`.

## Session contract

Karen receives these session artifacts:

```text
docs/cv.md
docs/job.md
docs/who_are_u.md       optional
repos/                  cloned evidence
company_info.md
out/                    writable evaluator output
```

The protected `anti_karen/` directory is not mounted in the evaluator container. After execution,
the wrapper copies the raw report into its artifacts area; the pipeline then validates and archives
that report.

The evaluator image has a dedicated non-root user and no `sudo`. The runtime drops every Linux
capability, enables `no-new-privileges`, limits process count, mounts evidence read-only and exposes
only `out/` for session writes. The image contains exactly one of agy, Claude Code or Codex. Each
adapter applies a read-only evaluation policy: agy uses its sandbox, Claude permits only read/search
tools, and Codex uses `read-only` with approval prompts disabled.

## Execution

Pass the absolute session directory returned by `harvey_guy.pipeline start-session`:

```fish
./karen_guard/run.sh --agent "$AGENT_PROVIDER" --state "$STATE_PATH" "$SESSION_DIR" \
    > "$SESSION_DIR/anti_karen/logs/karen.stdout.log" \
    2> "$SESSION_DIR/anti_karen/logs/karen.stderr.log"
```

Passing the canonical state makes the wrapper reject a mismatched provider or stale session before
it builds or launches a container. The `--state` option is optional only for isolated diagnostics.

After this wrapper returns, `record-evaluation` validates the report and uses `PIPELINE_DATA_DIR`
for the transactional convenience copy `evaluation.md`. The wrapper itself never publishes to the
data directory. The canonical archived report remains under the run's `iterations/` directory.

The image is rebuilt from the current source context on every invocation; the container engine
reuses unchanged layers. Authentication may run interactively in a separate container. During the
evaluation only the selected credential file is mounted, read-only; other providers' credentials
are absent. Provider transport still requires network access, but Karen's shell/content tools are
restricted and instructed not to perform network operations. This is not a domain-level egress
firewall, so provider isolation must still be tested end to end when quota is available.
