# Agent Architecture Guide

This document describes how the Actor-Critic multi-agent system is structured, how agents communicate, and what conventions to follow when creating or modifying agents.

---

## The Actor-Critic Pattern

The system uses three agent roles in a feedback loop:

| Role | Agent | Description |
|---|---|---|
| **Orchestrator** | Harvey (you) | Drives the loop. Reads runbooks sequentially, manages state variables, spawns subagents, and makes gatekeeper decisions. |
| **Critic** | Karen Guard | Evaluates the CV against real evidence (code, job description). Produces a scored report. Runs in total isolation. |
| **Actor** | Bill | Rewrites the CV based on Karen's report. Constrained to facts verified in the candidate's background. |

The loop runs until `FIT_SCORE >= MIN_FIT_SCORE` or `CURRENT_LOOP >= MAX_LOOPS`.

---

## Agent Types

### 1. Orchestrator (this agent)
Reads `harvey_guy/main.md` sequentially, line by line. Owns all loop state variables (`SESSION_ID`, `CURRENT_LOOP`, `FIT_SCORE`, etc.). Never delegates control permanently — always waits for subagents to complete before continuing.

### 2. Claude Subagents
Spawned by the orchestrator for tasks that would saturate its context window. Each subagent:
- Receives a **runbook path** and a set of **input variables** from the orchestrator.
- Reads its own `main.md` and executes the steps within it.
- Writes outputs to `SESSION_DIR` (never to the host repository).
- Reports completion back to the orchestrator and stops.

Current Claude subagents: **Harvey Shadow**, **Bill**, **Dependency Checker**.

### 3. External Agent (Karen Guard)
Runs as a Gemini CLI (`agy`) process inside a Docker container. Not a Claude subagent — it has its own model, authentication, and execution environment. Communicates exclusively via files mounted into the container:
- **Reads**: `SESSION_DIR/docs/` and `SESSION_DIR/repos/`
- **Writes**: `SESSION_DIR/evaluation.md`
- **Cannot access**: `SESSION_DIR/anti_karen/` (enforced via prompt restriction)

---

## Communication Protocol

Agents do not share memory or pass data via function arguments. All state is communicated through files in the session directory.

```
/tmp/karen_guard_<SESSION_ID>/
├── docs/               ← input documents (cv.md, job.md, who_are_u.md)
├── repos/              ← cloned candidate repositories (read-only for all)
├── company_info.md     ← company research output from Harvey Shadow
├── evaluation.md       ← Karen's raw output (moved to anti_karen/ by run.sh)
└── anti_karen/         ← protected zone: Karen cannot read this
    ├── karen_guard_core.log
    ├── karen_output.md ← final parsed evaluation report
    ├── draft_notes.txt ← Bill's internal scratchpad
    └── who_are_u.md    ← candidate background (if KAREN_READS_BACKGROUND=no)
```

The orchestrator reads `SESSION_DIR` to extract outputs after each agent completes.

---

## Isolation & Sandboxing

| Boundary | Mechanism |
|---|---|
| Karen cannot read `anti_karen/` | Prompt restriction in `prompt_persona.txt` |
| Karen cannot read host files | Docker volume mount: only `SESSION_DIR` is exposed |
| Bill cannot modify host repository | Explicit rule in `billf/main.md` |
| CV in repo is never modified during loop | SANDBOXING RULE in `harvey_guy/main.md` |
| Karen's `agy` config is isolated per session | `.gemini/` copied into `SESSION_DIR/.gemini/` |

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
