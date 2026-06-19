# Agent Architecture Guide

This document describes how the Actor-Critic multi-agent system is structured, how agents communicate, and what conventions to follow when creating or modifying agents.

---

## The Actor-Critic Pattern

The system uses three agent roles in a feedback loop:

| Role | Agent | Description |
|---|---|---|
| **Orchestrator** | Harvey (you) | Drives the loop. Reads runbooks sequentially, manages state variables, spawns agents, and makes gatekeeper decisions. |
| **Critic** | Karen Guard | Evaluates the CV against real evidence (code, job description). Produces a scored report. Runs in total isolation. |
| **Actor** | Bill | Rewrites the CV based on Karen's report. Constrained to facts verified in the candidate's background. |

The loop runs until `FIT_SCORE >= MIN_FIT_SCORE` or `CURRENT_LOOP >= MAX_LOOPS`.

Two **support agents** bracket the core loop without participating in it:

| Phase | Agent | Description |
|---|---|---|
| **Pre-loop** | Vera | Roleplay onboarding that produces `who_are_u.md` (Bill's source of truth). Optional — skipped if a usable file is reused. |
| **Post-loop** | Donna | Reads the final evaluation and writes `action_plan.md`: prioritized gaps, interview prep, and projects to raise the next score. |

---

## Agent Types

### 1. Orchestrator (this agent)
Reads `harvey_guy/main.md` sequentially, line by line. Owns all loop state variables (`SESSION_ID`, `CURRENT_LOOP`, `FIT_SCORE`, etc.). Never delegates control permanently — always waits for agents to complete before continuing.

### 2. Agents
Spawned by the orchestrator for tasks that would saturate its context window. Each agent:
- Receives a **runbook path** and a set of **input variables** from the orchestrator.
- Reads its own `main.md` and executes the steps within it.
- Writes outputs to `SESSION_DIR` (never to the host repository).
- Reports completion back to the orchestrator and stops.

Current agents: **Vera**, **Harvey Shadow**, **Bill**, **Donna**, **Dependency Checker**.

Note: **Vera** and **Donna** run outside the session loop and write directly to their designated host output in `data/docs/` (`who_are_u.md` and `action_plan.md` respectively), since no `SESSION_DIR` exists pre-loop / the loop is already over post-loop. This is the same legitimate-output pattern as the orchestrator writing `job.md` in Phase 1.

### 3. External Agent (Karen Guard)
Runs as a Gemini CLI (`agy`) process inside a containerized sandbox. Not a spawned agent — it has its own model, authentication, and execution environment. Communicates exclusively via the subpaths mounted into the container:
- **Reads** (read-only mounts): `SESSION_DIR/docs/`, `SESSION_DIR/repos/`, `SESSION_DIR/company_info.md`
- **Writes**: `SESSION_DIR/out/evaluation.md` (the only writable mount); `run.sh` then relocates it to `anti_karen/karen_output.md`
- **Cannot access**: `SESSION_DIR/anti_karen/` — physically, because it is not mounted into the container at all (not merely a prompt restriction)

---

## Communication Protocol

Agents do not share memory or pass data via function arguments. All state is communicated through files in the session directory.

```
/tmp/karen_guard_<SESSION_ID>/
├── docs/               ← input documents (cv.md, job.md, who_are_u.md) — mounted read-only to Karen
├── repos/              ← cloned candidate repositories — mounted read-only to Karen
├── company_info.md     ← company research output from Harvey Shadow — mounted read-only to Karen
├── out/                ← Karen's only writable mount; she writes out/evaluation.md here
└── anti_karen/         ← protected zone: NOT mounted into Karen's container
    ├── karen_guard_core.log
    ├── evaluation.md   ← relocated from out/ by run.sh
    ├── karen_output.md ← final parsed evaluation report
    ├── draft_notes.txt ← Bill's internal scratchpad
    └── who_are_u.md    ← candidate background (if KAREN_READS_BACKGROUND=no)
```

Per-iteration artifacts are also archived to a host-side run history at `.runs/<timestamp>/loop_NN/` (input/output CVs, Karen's report, score) with a `scores.csv` progression — see the orchestrator runbook. The orchestrator reads `SESSION_DIR` to extract outputs after each agent completes.

---

## Isolation & Sandboxing

| Boundary | Mechanism |
|---|---|
| Karen cannot read `anti_karen/` | **Physical**: `run.sh` mounts only `docs/`, `repos/`, `company_info.md`, `out/` into the container — `anti_karen/` is never present. Prompt restriction in `prompt_persona.txt` is a redundant second layer. |
| Karen cannot read host files | Container volume mounts: only the subpaths above are exposed (`docs/`/`repos/` read-only) |
| Karen writes only her report | Only `out/` is mounted writable; she writes `out/evaluation.md`, which `run.sh` relocates to `anti_karen/` |
| Bill cannot modify host repository | Explicit rule in `billf/main.md` |
| CV in repo is never modified during loop | SANDBOXING RULE in `harvey_guy/main.md` |
| Karen's `agy` config is isolated per session | `.gemini/` copied into `SESSION_DIR/.gemini/` |
| Vera writes only `data/docs/who_are_u.md` | Single-output rule in `vera_psyco/main.md` |
| Donna writes only `data/docs/action_plan.md` | Single-output rule in `donna_nana/main.md` |

---

## How to Add a New Agent

1. Create a directory: `<agent_name>/`
2. Write `<agent_name>/main.md` following this structure:
   - **`# <AgentName>: <Role> Guide`** — one-line purpose
   - **`## 📥 Inputs`** — variables the orchestrator will pass
   - **`## 🔒 Security & Data Isolation Rules`** — what the agent must not touch
   - **`## 🛠️ Step-by-Step Execution Plan`** — numbered steps, explicit commands
3. Add the agent to the orchestrator flow in `harvey_guy/main.md`.
4. Add a row to the Agent Roster table in `main.md` (root).
5. Write a `README.md` documenting the agent's role and outputs.

---

## State Variables Reference

| Variable | Set by | Used by |
|---|---|---|
| `SESSION_ID` | Harvey Python script (stdout) | Orchestrator, Shadow, Karen, Bill |
| `SESSION_DIR` | Orchestrator (derived: `/tmp/karen_guard_$SESSION_ID/`) | All agents |
| `CURRENT_LOOP` | Orchestrator (init: `0`, inc: after Bill) | Gatekeeper |
| `MAX_LOOPS` | User (Phase 1) | Gatekeeper |
| `MIN_FIT_SCORE` | User (Phase 1) | Gatekeeper |
| `FIT_SCORE` | Orchestrator (parsed from `karen_output.md`) | Gatekeeper |
| `KAREN_REPORT_PATH` | Orchestrator (last line of `karen_run.log`) | Bill |
| `KAREN_READS_BACKGROUND` | User (Phase 1), exported as env var | Harvey Python script |
