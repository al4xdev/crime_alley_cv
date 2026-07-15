# From prose orchestration to measurable agent boundaries: an experimental validation report

**Date:** 2026-07-15  
**System:** Crime Alley CV / Meta 2028  
**Status:** engineering report; not peer reviewed

## Abstract

This report describes the design, implementation and validation of a prose-driven multi-agent CV
optimization pipeline. The work investigated whether nondeterministic agents can remain responsible
for contextual judgment while deterministic software owns state, recovery, artifact integrity and
measurement. The resulting system uses a forward-only transactional control plane, provider-neutral
CLI adapters for agy, Claude Code and Codex, isolated evaluator containers, and an optional
content-only evaluator named The Celestial. Validation combined static analysis, typed schemas,
offline replay, fault-oriented tests, container builds, authentication checks and two live file-edit
smoke tests. Claude Haiku 4.5 completed its isolated edit directly. Codex exposed two container
sandbox incompatibilities before completing the same edit under an explicit Docker-owned write
boundary. The experiments support the architectural separation between model judgment and
deterministic invariants, but do not establish comparative model quality or full benchmark validity.

## 1. Research questions

The work addressed five questions:

1. Can natural-language runbooks coordinate specialized agents without owning mutable control
   state?
2. Can interrupted transitions be resumed without silently accepting stale or unauthenticated
   artifacts?
3. Can multiple agent CLIs share a common execution contract while retaining their native login and
   subscription behavior?
4. Can agent content be evaluated with one metric architecture while changing only the dynamic role
   description and observed conversation?
5. Do the declared authentication and write boundaries work in real provider containers, rather
   than only in mocks?

## 2. System under study

The pipeline contains six logical roles. Vera optionally elicits candidate background; Harvey owns
orchestration; Harvey Shadow gathers public evidence; Karen evaluates the CV; Bill revises it; and
Donna produces a development plan. Markdown runbooks define judgment-intensive work. Python owns
phase transitions, evaluation counts, score parsing, transaction recovery, guard digests and final
artifact publication.

The canonical run layout is:

```text
.runs/<run-id>/
├── state.json
├── events.jsonl
├── scores.csv
├── transactions/
└── iterations/<NN>/
    ├── cv_in.md
    ├── evaluation.md
    ├── evaluation.json
    ├── cv_out.md
    └── draft_notes.txt
```

Each model-facing transition is forward-only. A transaction is staged with a strict manifest,
operation identity, revision, target allowlist and payload hashes. Recovery validates those values
before publishing. Bill and Donna receive digest-anchored guards over their read-only context,
including relevant canonical inputs, archived evaluations, cloned repositories and host worktree
state. The rule implemented by this design is: **judgment lives in prose; invariants live in code**.

## 3. The Celestial measurement protocol

The Celestial evaluates conversation content, not source code, infrastructure, permissions, tools or
hidden reasoning. Each observed role receives a dynamic description and role-specific anchors, but
all roles share eight dimensions:

1. clarity;
2. role alignment;
3. relevance and focus;
4. internal consistency;
5. grounding and evidence discipline;
6. completeness and coverage;
7. usefulness and actionability;
8. uncertainty calibration.

Instruction design and execution/output are scored independently from 0 through 4 and each panel
contributes 50% to a global 0–100 index. The protocol performs three repetitions per observed item,
a one-shot CV baseline, and three order-swapped pairwise comparisons between the baseline and final
CV. At most one schema repair and one bounded verification batch are allowed per repetition.

Cases are frozen before any model call. The case digest covers immutable envelopes, initial/final CV,
job description and a bounded allowlisted evidence corpus. Baselines and judge outputs live outside
the case. Interrupted benchmarks validate existing structured results and resume only missing work;
the completed manifest is written only after every required result succeeds. Schema-v1 artifacts are
audit-only and cannot be mixed into the v2 protocol.

Human tasks use opaque IDs and randomized A/B order. Candidate name and common contact identifiers
are redacted, although unusual PII still requires manual review. Metrics that depend on human ground
truth require two independent raters. The report distinguishes repeatability, human agreement,
human/model agreement, evidence precision, revision acceptance, unsupported-claim reduction and
sensitivity across compatible judges. No metric controls the production pipeline.

## 4. Methods

### 4.1 Offline engineering validation

The deterministic control plane was tested without provider calls. The suite used temporary data,
run, session and Celestial roots. Tests covered exact score parsing, iteration limits, recovery,
manifest and payload integrity, path/symlink guards, stale artifacts, capture freezing, corpus
limits, citation validation, resumable evaluation, blind labels and metric availability.

Static validation consisted of Ruff, strict mypy checks, Bash/POSIX shell/Fish syntax checks, JSON
parsing and `git diff --check`. CI repeats these checks and builds provider-specific evaluator images.
Provider binaries and base images are pinned by version and digest; Python dependencies are frozen in
`uv.lock`.

### 4.2 Container and authentication validation

The outer image and dedicated Claude/Codex Celestial images were built locally. Authentication was
tested by mounting exactly one host credential read-only, copying it into an ephemeral `tmpfs` home,
and running the provider's status command with account output suppressed. This test discovered that
the home `tmpfs` was initially owned by root. Assigning `uid=1000`, `gid=1000` and mode `0700` fixed
both providers without broadening the mounted credential.

### 4.3 Live edit protocol

Two separate host directories under `/tmp` contained a two-line file:

```text
status=pending
provider=<provider>
```

Each container received only its own credential and its corresponding directory at `/work`. The
repository was not mounted. Container capabilities were dropped, `no-new-privileges` was enabled,
the root filesystem was read-only, and only `/work` plus ephemeral `tmpfs` paths were writable. The
model was asked to replace the status line and preserve the provider line.

Claude used the pinned model `claude-haiku-4-5-20251001`, with only `Read` and `Edit` available.
Codex used the locally configured `gpt-5.6-sol` with low reasoning effort and web search disabled.

## 5. Results

### 5.1 Deterministic and build results

| Check | Result |
|---|---:|
| Python tests after the final sandbox regression | 93 passed |
| Ruff | passed |
| mypy | passed |
| Shell syntax and whitespace validation | passed |
| Outer Docker image | built |
| Dedicated Claude Celestial image | built |
| Dedicated Codex Celestial image | built |
| Claude container authentication status | passed |
| Codex container authentication status | passed |

The suite count is a point-in-time observation; the repository's current CI result remains the
canonical value after subsequent changes.

### 5.2 Live Claude result

Claude Haiku completed the edit in approximately 9.1 seconds. The resulting file was:

```text
status=edited-by-claude
provider=claude
```

The process exited successfully. Usage metadata was not collected because the smoke test requested
plain text output. This experiment validates authentication, model selection, tool availability and
write access to the single mounted directory; it does not validate the complete CV pipeline.

### 5.3 Live Codex results and negative controls

Codex required four observations. The failures were retained because they falsified assumptions in
the original container contract.

| Attempt | Boundary | Outcome | Observed usage |
|---|---|---|---|
| 1 | Internal `workspace-write`; output suppressed | interrupted after about 100 s; file unchanged | unavailable |
| 2 | Internal `workspace-write`; no `bubblewrap` installed | failed explicitly before editing | 28,408 input (24,832 cached), 242 output |
| 3 | Internal `workspace-write`; `bubblewrap` installed | kernel denied nested unprivileged namespace | 38,212 input (28,672 cached), 320 output |
| 4 | Docker-owned boundary; Codex internal sandbox disabled | succeeded in about 16.8 s | 27,770 input (22,784 cached), 142 output |

The successful file was:

```text
status=edited-by-codex
provider=codex
```

The successful configuration did not mean unrestricted host access. `danger-full-access` disabled
the *nested Codex sandbox*, while Docker still supplied the actual boundary: read-only container
root, dropped capabilities, no repository mount, read-only credential and one writable `/work`
mount. This distinction is now explicit in the evaluator adapter. `bubblewrap` remains installed in
runtime images for environments where nested user namespaces are permitted and for the broader
outer runtime, but it cannot be assumed to work on every Docker host.

Across the three Codex attempts with reported usage, input was 94,390 tokens, of which 76,288 were
cached, and output was 704 tokens. The first interrupted attempt did not expose usage. These values
describe CLI-reported tokens, not an independently verified billing amount.

## 6. Findings

1. **Forward-only ownership reduced ambiguity.** Moving counters, persistence and artifact
   publication out of runbooks made offline replay and crash recovery testable.
2. **Mocks were insufficient for container permissions.** Static flags and authentication mocks did
   not reveal root-owned `tmpfs`, the missing sandbox helper or the host kernel's namespace policy.
3. **A sandbox must have one named owner.** Nesting Codex's Linux sandbox inside a restricted Docker
   container was not portable. The evaluator now treats Docker mounts as the authoritative write
   boundary instead of claiming two independent sandboxes.
4. **Content measurement must expose unavailable evidence.** Human-ground-truth metrics remain
   unavailable until two raters label the same item; model preference is not presented as hiring
   impact.
5. **Provider neutrality is contractual, not identical.** The same high-level edit contract required
   different tool and confinement strategies for Claude and Codex.

## 7. Threats to validity

- The live task was deliberately trivial and cannot predict performance on CV evaluation,
  repository research or multi-step revision.
- Only one Claude model and one Codex model were called once successfully.
- The Codex result depends on Docker being the trusted write boundary; other runtimes must reproduce
  equivalent read-only mounts and capability restrictions.
- No live The Celestial baseline or repeated judging benchmark was executed, so subscription
  accounting, long-run resumption and provider-side structured-output behavior remain unverified.
- agy authentication and live prompt behavior were not part of these experiments.
- PII redaction is deterministic but not a substitute for human disclosure review.
- Model outputs and provider infrastructure can vary even when the environment and model ID are
  fixed.

## 8. Reproducibility and safety notes

The repository CI is the reproducible offline protocol. Live tests should use disposable content,
an exact model ID, one read-only credential mount and the smallest writable directory possible.
Raw credentials, account-status output and provider response logs must not be committed. The
`.celestial/` directory is ignored because it can contain CV content and raw judge responses.

The current Claude Haiku model ID was checked against Anthropic's model documentation before the
test. Future repetitions should re-check model availability and record CLI/image versions, host
kernel policy, elapsed time and provider-reported usage.

## 9. Conclusion

The experiments provide evidence that the pipeline's deterministic core, provider authentication
and minimal live editing path operate as intended after correcting three boundary defects. They also
show why tool permissions cannot be inferred from command-line flags alone. The next scientifically
useful experiment is a small, pre-registered Celestial run over synthetic CV data, followed by two
independent human raters. That experiment should preserve the present quota estimate, frozen-case
digest and explicit unavailable-metric policy.

## References

- Anthropic, [Model IDs and versioning](https://platform.claude.com/docs/en/about-claude/models/model-ids-and-versions).
- Anthropic, [Models overview](https://platform.claude.com/docs/en/about-claude/models/overview).
- Project source: `harvey_guy/pipeline.py`, `config/agents/`, `karen_guard/` and
  `the_celestial/` in this repository.
