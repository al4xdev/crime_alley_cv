# Actor-Critic CV Optimization Loop

> [!IMPORTANT]
> **SEQUENTIAL EXECUTION RULE:**
> Read **[harvey_guy/main.md](harvey_guy/main.md)** once, then execute its phases in order. Treat
> the generated `state.json` as the only source of control-flow truth.

---

## What This System Does

This is a multi-agent pipeline that iteratively refines a candidate's CV against a job description until a minimum technical fit score is achieved. It uses an Actor-Critic architecture: one agent edits (Bill), one agent criticizes (Karen), and a deterministic gatekeeper decides whether to loop or exit. Around that core, an onboarding agent (Vera) seeds the candidate's background and a coaching agent (Donna) turns the final evaluation into a development plan.

## Agent Roster

| Agent | Role | Runtime |
|---|---|---|
| **Vera** | Onboarding. Roleplay interview that produces the candidate background (`who_are_u.md`). Optional, pre-loop; skipped if a usable file is reused. | agent |
| **Harvey** | Orchestrator. Initializes the session workspace and ingests documents. | Python (`uv run`) |
| **Harvey Shadow** | Infrastructure agent. Clones GitHub repos, researches the company, pre-builds the container image — in parallel with the orchestrator. | agent |
| **Karen Guard** | Evaluator/Critic. Reads the CV, job description, and actual repository code. Produces a skeptical technical evaluation with a fit score. | Selected agent CLI inside container |
| **Bill** | Editor/Actor. Reads Karen's report and rewrites the CV to address every criticism — without hallucinating credentials. | agent |
| **Donna** | Coach. Reads the final evaluation and writes a prioritized action plan (`action_plan.md`). Post-loop. | agent |

## How to Begin

1. Open **[harvey_guy/main.md](harvey_guy/main.md)**.
2. Collect the four run inputs in one interaction.
3. Initialize the canonical run and follow only the phase returned by the control plane.
