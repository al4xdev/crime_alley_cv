# Front 3 acceptance — CI, dependencies and runbooks

Date: 2026-07-15

Status: **accepted**

## Delivered

- One CI workflow runs frozen dependency installation, lint, strict typing, shell/JSON validation,
  tests and both container builds for pull requests, `main` and release tags.
- Publishing is gated by the check and container-build jobs, uses SHA-pinned actions, minimal job
  permissions, provenance and SBOM. The independent publish workflow was removed.
- Container and CI dependencies are aligned; the unused `at` daemon/package and stale persistent
  dependency-marker instructions were removed.
- Harvey, Donna, Vera and Karen runbooks use canonical commands and configurable paths. Donna's
  action-plan path is now a required validated contract field.
- `start.sh` maps configurable host data/run directories into stable container paths and forwards
  the session root; a subprocess test covers paths containing spaces.
- The unused duplicate `boundaries/layout.fish` was removed; canonical layout remains in Python.

## Validation

- `uv run pytest -q`: 67 passed.
- `uv run ruff check .`: passed.
- `uv run mypy --strict harvey_guy tools/replay_pipeline.py`: passed.
- Bash, POSIX sh, Fish and JSON syntax checks: passed.
- `git diff --check`: passed.
- `docker build --tag crime_alley_pipeline:front3-check .`: passed.
- Final bounded critique: `ACEITA`.

The final critique reused a dormant critic thread because the runtime rejected creation of an
additional context-free thread at its thread limit. It was instructed to ignore prior context and
review only the final bounded files. No provider-quota end-to-end execution was claimed.
