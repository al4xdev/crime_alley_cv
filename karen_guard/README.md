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
only `out/` for session writes. `agy` runs with `--sandbox`; unsandboxed commands, URL tools and MCP
are denied by its evaluator-specific permission file.

## Execution

Pass the absolute session directory returned by `harvey_guy.pipeline start-session`:

```fish
./karen_guard/run.sh "$SESSION_DIR" \
    > "$SESSION_DIR/anti_karen/logs/karen.stdout.log" \
    2> "$SESSION_DIR/anti_karen/logs/karen.stderr.log"
```

After this wrapper returns, `record-evaluation` validates the report and uses `PIPELINE_DATA_DIR`
for the transactional convenience copy `evaluation.md`. The wrapper itself never publishes to the
data directory. The canonical archived report remains under the run's `iterations/` directory.

The image is rebuilt from the current source context on every invocation; the container engine
reuses unchanged layers. Authentication may run interactively in a separate container. During the
evaluation only the OAuth token file is mounted, read-only. Provider transport still requires
network access, but Karen's shell/content tools are sandboxed and instructed not to perform network
operations. This is not a domain-level egress firewall, so provider isolation must still be tested
end to end when quota is available.
