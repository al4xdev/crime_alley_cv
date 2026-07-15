# The Celestial content benchmark — implementation record

Status: implemented on `feat/the-celestial-content-benchmark`.

## Scope and invariants

- Evaluate visible conversation content only; code, infrastructure, permissions and hidden
  reasoning are outside the score.
- Cover Vera, Harvey, Shadow, Karen, Bill and Donna when their content is observable.
- Use one shared eight-dimension rubric, role-specific descriptions/anchors, a 0–4 scale, two
  50/50 panels and a global 0–100 index.
- Capture locally on every Docker run without model calls. Benchmarking is optional, off by
  default and requires two explicit confirmations.
- Freeze cases by content digest before any baseline or judge call.
- Reject schema-v1 artifacts instead of silently mixing them with the v2 protocol.
- Require exact executor and fixed judge models. Report, rather than prohibit, self-judging.
- Generate the simple one-shot baseline with the executor provider/model.
- Judge each item three times; allow one repair total and one read-only verification batch of at
  most five excerpts per repetition.
- Preserve raw output and structured results under ignored `.celestial/`.
- Resume interrupted runs by validating existing results and evaluating only missing repetitions;
  seal the immutable manifest only when every evaluation and pairwise comparison succeeds.
- Keep all metrics observational and mark metrics that need human or downstream data unavailable.

## Delivered components

- Strict envelopes, profiles, evaluation and human-label schemas in `the_celestial/`.
- Immutable capture, bounded allowlisted evidence corpus and content-addressed frozen cases.
- Dynamic prompt compiler with prompt-injection boundaries and role-specific anchors.
- Dedicated Claude and Codex provider wrappers with explicit models and fail-closed no-tool
  capability checks. agy is intentionally blocked for Celestial calls until equivalent enforcement
  can be verified.
- Baseline, repeated evaluation, bounded verification, pairwise comparison and call estimator.
- Per-item repeatability, compatible-judge sensitivity, pairwise/simple-pipeline comparison and
  human-gated metrics. Blind-task export uses opaque IDs, randomized A/B order, candidate PII
  redaction and strict registered-task imports with two-rater metrics.
- Pipeline schema v3 metadata with schema-v2 read migration.
- Post-transition capture hooks for the agent lifecycle.
- Docker opt-in, warning, deferred execution, dedicated provider credential containers and second
  quota confirmation.
- Resumable hash-chained ledger and immutable completed benchmark manifests.

## Deliberately deferred evidence

No live prompt was sent to Claude Code or Codex during implementation. Authenticated end-to-end
behavior, subscription accounting and provider-side enforcement require a future low-quota smoke
test. Local CLI capability help, offline provider-command tests and both dedicated image builds can
be validated without a model prompt. The warning remains visible in both `start.sh` and the README.
