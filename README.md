# Job-Stack & Karen Guard

Automated CV optimization system based on a multi-agent Actor-Critic architecture. An orchestrator drives a feedback loop where a critic agent (Karen) scores the CV against real code evidence, and an editor agent (Bill) rewrites it until the score meets the acceptance threshold.

---

## How It Works

```
main.md → harvey_guy/main.md (runbook)
  → Phase 0 → Phase 1 → Phase 1.5 (Vera, optional)
  → Loop [Harvey → Karen → Gatekeeper → Bill]
  → Post-Loop (Donna)
```

Before the loop, Vera optionally seeds the candidate background. Each loop iteration: Harvey sets up the session workspace, Karen evaluates the CV against the candidate's actual repositories, the Gatekeeper decides whether to exit or refine, and Bill rewrites the CV based on Karen's report. After the loop, Donna turns the final evaluation into an action plan.

---

## Agent Roster

| Agent | Directory | Runtime | Role |
|---|---|---|---|
| **Vera** | `vera_guy/` | Claude subagent | Onboarding interview → `who_are_u.md` (optional, pre-loop) |
| **Harvey** | `harvey_guy/` | Python + Claude subagent | Orchestrator & context collector |
| **Harvey Shadow** | `harvey_guy/` | Claude subagent | Clones repos, researches company, pre-builds Docker |
| **Karen Guard** | `karen_guard/` | Gemini CLI inside Docker | Skeptical evaluator & critic |
| **Bill** | `billf/` | Claude subagent | CV editor & actor |
| **Donna** | `donna_guy/` | Claude subagent | Coach → `action_plan.md` (post-loop) |

---

## Modules

- [Vera (Onboarding)](vera_guy/README.md) — Roleplay interview that produces the candidate background.
- [Harvey (Orchestrator)](harvey_guy/README.md) — Session setup, document ingestion, subagent orchestration.
- [Karen Guard (Evaluator)](karen_guard/README.md) — Isolated Docker evaluation environment.
- [Bill (Editor)](billf/README.md) — CV revision based on Karen's report.
- [Donna (Coach)](donna_guy/README.md) — Post-loop action plan from the final evaluation.

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
- `who_are_u.md` — candidate background (recommended; Vera can generate it in Phase 1.5 if missing)

Pipeline-generated outputs in `data/docs/`:
- `action_plan.md` — written by Donna after the loop

See [requirements.md](requirements.md) for system dependencies.

---

## 🚀 How to Run

This pipeline is designed to be executed by an autonomous coding agent (such as **Antigravity CLI / `agy`** or **Claude Code**) running directly in your terminal at the root of this repository.

### Setup and Start:

1. **Open your agent client** in the repository root:
   ```bash
   agy
   ```
   *(or use `claude` / your preferred agent CLI).*

2. **Trigger the loop** by asking the agent to read and follow the instructions in the main starter file:
   > **User Prompt:**
   > *(or simply reference: `@main.md`)*

3. **Follow along:** The agent will spawn a subagent to check requirements, ask you the configuration questions (Phase 1), and execute the refinement loops autonomously.
