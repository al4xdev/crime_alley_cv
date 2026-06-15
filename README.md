# Job-Stack & Karen Guard

Automated CV optimization system based on a multi-agent Actor-Critic architecture. An orchestrator drives a feedback loop where a critic agent (Karen) scores the CV against real code evidence, and an editor agent (Bill) rewrites it until the score meets the acceptance threshold.

---

## How It Works

```
main.md → harvey_guy/main.md (runbook) → Phase 0 → Phase 1 → Loop [Harvey → Karen → Gatekeeper → Bill]
```

Each loop iteration: Harvey sets up the session workspace, Karen evaluates the CV against the candidate's actual repositories, the Gatekeeper decides whether to exit or refine, and Bill rewrites the CV based on Karen's report.

---

## Agent Roster

| Agent | Directory | Runtime | Role |
|---|---|---|---|
| **Harvey** | `harvey_guy/` | Python + Claude subagent | Orchestrator & context collector |
| **Harvey Shadow** | `harvey_guy/` | Claude subagent | Clones repos, researches company, pre-builds Docker |
| **Karen Guard** | `karen_guard/` | Gemini CLI inside Docker | Skeptical evaluator & critic |
| **Bill** | `billf/` | Claude subagent | CV editor & actor |

---

## Modules

- [Harvey (Orchestrator)](harvey_guy/README.md) — Session setup, document ingestion, subagent orchestration.
- [Karen Guard (Evaluator)](karen_guard/README.md) — Isolated Docker evaluation environment.
- [Bill (Editor)](billf/README.md) — CV revision based on Karen's report.

---

## Architecture

- [Agent Architecture Guide](style.md) — How agents communicate, isolation model, state variables, and how to add new agents.
- [Orchestrator Runbook](harvey_guy/main.md) — The full execution runbook (start here after `main.md`).

---

## Session Layout

Each run creates an isolated session directory:

```
/tmp/karen_guard_<UUID>/
├── docs/           ← cv.md, job.md, who_are_u.md
├── repos/          ← cloned candidate repositories
├── company_info.md ← company research
└── anti_karen/     ← protected zone (Karen cannot read)
    ├── karen_output.md
    └── karen_guard_core.log
```

---

## Prerequisites

`data/docs/` must contain at minimum:
- `cv.md` — candidate's resume in Markdown
- `job.md` — job description (written by the orchestrator in Phase 1)
- `who_are_u.md` — candidate background (optional but recommended)

See [requirements.md](requirements.md) for system dependencies.
