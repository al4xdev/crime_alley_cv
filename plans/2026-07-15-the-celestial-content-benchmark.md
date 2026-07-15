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
- Require exact executor and fixed judge models. Report, rather than prohibit, self-judging.
- Generate the simple one-shot baseline with the executor provider/model.
- Judge each item three times; allow one repair total and one read-only verification batch of at
  most five excerpts per repetition.
- Preserve raw output and structured results under ignored `.celestial/`.
- Keep all metrics observational and mark metrics that need human or downstream data unavailable.

## Delivered components

- Strict envelopes, profiles, evaluation and human-label schemas in `the_celestial/`.
- Immutable capture and content-addressed frozen cases.
- Dynamic prompt compiler with prompt-injection boundaries and role-specific anchors.
- agy, Claude and Codex provider wrappers with explicit models and judge tool restrictions.
- Baseline, repeated evaluation, bounded verification, pairwise comparison and call estimator.
- Metrics/report generation plus blind-task export and label import.
- Pipeline schema v3 metadata with schema-v2 read migration.
- Post-transition capture hooks for the agent lifecycle.
- Docker opt-in, warning, deferred execution, dedicated provider credential containers and second
  quota confirmation.

## Deliberately deferred evidence

No live prompt was sent to Claude Code or Codex during implementation. Authenticated end-to-end
behavior, subscription accounting and provider-side enforcement require a future low-quota smoke
test. The warning remains visible in both `start.sh` and the README.
