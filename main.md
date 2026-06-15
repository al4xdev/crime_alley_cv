# Actor-Critic CV Optimization Loop

> [!IMPORTANT]
> **SEQUENTIAL EXECUTION RULE:**
> Read and execute **[harvey_guy/main.md](harvey_guy/main.md)** in strict sequential, line-by-line order.
> Do **NOT** read the entire file at once or pre-analyze the whole process. This preserves the interactive feedback loop and architectural sanity.

---

## What This System Does

This is a multi-agent pipeline that iteratively refines a candidate's CV against a job description until a minimum technical fit score is achieved. It uses an Actor-Critic architecture: one agent edits (Bill), one agent criticizes (Karen), and a deterministic gatekeeper decides whether to loop or exit. Around that core, an onboarding agent (Vera) seeds the candidate's background and a coaching agent (Donna) turns the final evaluation into a development plan.

## Agent Roster

| Agent | Role | Runtime |
|---|---|---|
| **Vera** | Onboarding. Roleplay interview that produces the candidate background (`who_are_u.md`). Optional, pre-loop; skipped if a usable file is reused. | Claude subagent |
| **Harvey** | Orchestrator. Initializes the session workspace and ingests documents. | Python (`uv run`) |
| **Harvey Shadow** | Infrastructure subagent. Clones GitHub repos, researches the company, pre-builds the Docker image — in parallel with the orchestrator. | Claude subagent |
| **Karen Guard** | Evaluator/Critic. Reads the CV, job description, and actual repository code. Produces a skeptical technical evaluation with a fit score. | Gemini CLI (`agy`) inside Docker |
| **Bill** | Editor/Actor. Reads Karen's report and rewrites the CV to address every criticism — without hallucinating credentials. | Claude subagent |
| **Donna** | Coach. Reads the final evaluation and writes a prioritized action plan (`action_plan.md`). Post-loop. | Claude subagent |

## How to Begin

1. Open **[harvey_guy/main.md](harvey_guy/main.md)**.
2. Read the Global Agent Execution Rules at the top.
3. Execute **Phase 0: Dependency Verification**, **Phase 1: Initialize State**, then **Phase 1.5: Candidate Onboarding (Vera)**, step-by-step.
