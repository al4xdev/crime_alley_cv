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

---

## 🧪 Design Decisions & Philosophy

> **This is a study project.** Its real subject is not CV optimization — that is the
> excuse. The subject is **orchestrating a multi-agent system primarily in natural
> language**, with deterministic code only where it genuinely earns its place. The
> decisions below are the lessons that shaped the architecture; they are written down so
> the *why* survives, not just the *what*.

### The core bet

The pipeline is orchestrated by an LLM reading runbooks (`harvey_guy/main.md` and the
per-agent `main.md` files) as prose instructions, not by a program calling functions.
This is deliberately the opposite of a hardcoded workflow engine. The bet is that a capable
agent runtime (Claude Code, `agy`) is a good-enough "interpreter" for an orchestration
written in prose — and that the flexibility this buys (easy to read, easy to change, no
brittle glue) outweighs the guarantees you give up. The rest of this section is about
*which* guarantees you give up, and when that matters.

### What natural-language orchestration actually costs

**1. There is no runtime that holds your state.** A normal program has a call stack and
variables that persist for you. Prose orchestration has neither. `CURRENT_LOOP`,
`FIT_SCORE`, `SESSION_ID` live only in the orchestrator's context window unless you
**materialize them into files**. This is the most underestimated part of the approach: state
that isn't written to disk doesn't really exist. Hence the loop-state checkpoint and the
file-based session layout.

**2. "Sequential execution" is a preference, not a guarantee.** The runbooks ask the agent
to execute step by step and not read ahead — but the model loads the whole file into context
at once. You cannot *force* sequencing the way an interpreter does. This is a fundamental
limit of the medium, not a bug to fix. The mitigation is to make steps gated by checked
preconditions (a file exists, a value is set) so order is enforced by data dependencies, not
by reading discipline.

**3. Handoffs between agents are file contracts, not function signatures.** With no shared
memory and no types, the "protocol" is literally *"Karen writes `## Technical Fit Score: N/100`
and the orchestrator parses that line."* That is brittle exactly where a typed function call
would be rigid. So a large part of the work is making these contracts **explicit and
parseable** — the mandated `job.md` first-line format, the exact score line, the
`company_info.md` section template. A contract that isn't written down drifts.

### The governing heuristic: migrate only what fails *silently*

The instinct from classic engineering is "move invariants into code." That instinct is
**wrong here**, because the runtime is not dumb — it is a reasoning agent that self-heals.
When a failure announces itself (a score doesn't parse, a file is missing, a path is
malformed), the agent notices and recovers; hardcoding those cases trades graceful
degradation for rigid failure. A regex score-parser *breaks* on a format the LLM would have
read fine.

The failures worth making deterministic are the ones that produce a **plausible, wrong
result with no error signal** — because self-healing needs an error to react to, and there is
none. The original broken feedback loop was exactly this: Karen kept scoring the *original*
CV every iteration, produced perfectly normal-looking scores, and nothing appeared broken.

> **Rule of thumb:** migrate to deterministic code only what fails **silently**. What fails
> **loudly**, leave for the agent to heal in prose.

| Concern | Fails how? | Lives where |
|---|---|---|
| Score parsing, file paths, retries | Loudly (visible error) | Prose — the agent heals it |
| Vera/Karen/Bill/Donna judgment | "Worse result", recoverable | Prose — this *is* the value |
| CV carry-forward, loop semantics | Silently (plausible but wrong) | Lean toward code |
| Reading files Karen must not see | Silently (report looks normal) | Code — physical, not instruction |

### Isolation is graduated, and the mechanism should match the stakes

There are two kinds of boundary in this system: **physical** (strong — Karen runs in Docker
and can only see what is mounted) and **instructional** (weak, best-effort — "you MUST NOT
read `anti_karen/`" in the prompt). Both are legitimate, but they are not interchangeable.
A boundary protecting something that matters — and whose violation would be *silent* — should
be physical. (See `backlog.md` FEAT-B: today `anti_karen/` is still inside Karen's mount, so
that boundary is currently instructional; making it physical is the one hardening worth
doing.)

### Observability is the human safety net

Every run writes a full trail to its session directory under `/tmp/karen_guard_<uuid>/`
(logs, reports, intermediate CVs). Because a human inspects that directory, "silent" failures
are not truly silent to the operator — which further justifies *not* over-engineering
deterministic scaffolding. The planned run-versioning (`backlog.md` FEAT-A) exists to make
this trail consolidated and comparable across iterations rather than scattered.

### Where this matures

The honest trajectory: invariants critical to correctness tend to migrate to the
deterministic side **over time, as the pain is felt** — not front-loaded. Prose keeps the
judgment; code gradually absorbs the invariants. That is the natural maturation of this kind
of system, and treating it as a destination to rush toward would defeat the point of the
study. The boundary between code and language is itself the thing being learned here.
