# Donna (Coach)

Career coaching agent. After the optimization loop exits, Donna reads Karen's final evaluation and produces a concrete, prioritized development plan (`data/docs/action_plan.md`).

Donna operates as a subagent, invoked **once after the loop** by the orchestrator, on both exit paths (target reached or max loops).

---

## Why Donna Exists

The loop produces a better CV, but a CV is only a snapshot. The evaluation report contains a wealth of signal about what the candidate should actually build, study, and rehearse to raise their score on the next run. Donna converts the critic's findings into a forward-looking plan instead of letting them die in a report file.

---

## Inputs

| Variable | Source |
|---|---|
| `SESSION_ID` | Orchestrator |
| `KAREN_REPORT_PATH` | Orchestrator (final evaluation report) |
| `FIT_SCORE` | Orchestrator (final score achieved) |
| `MIN_FIT_SCORE` | Orchestrator (target from Phase 1) |

---

## Output

| File | Description |
|---|---|
| `data/docs/action_plan.md` | Prioritized plan: technical gaps, interview prep, public projects to build, sequenced next steps |

Every recommendation is grounded in a specific finding from Karen's report or an unmet job requirement, no generic career advice.

---

## Runbook

[`main.md`](main.md)
