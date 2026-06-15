# Vera (Onboarding)

Candidate onboarding agent. Conducts a structured roleplay conversation to produce `data/docs/who_are_u.md`, the source-of-truth background document that anchors the entire pipeline against hallucination.

Vera operates as a agent, invoked **once before the optimization loop** and only when needed. She is **optional**: if a usable `who_are_u.md` already exists, the orchestrator reuses it and skips Vera.

---

## Why Vera Exists

`who_are_u.md` is Bill's absolute source of truth, he is forbidden from inventing any role, technology, or credential not present in it. But without an onboarding process, candidates rarely write a good one. Vera turns that gap into a guided 10-minute interview.

---

## When Vera Runs

| Situation | Orchestrator behavior |
|---|---|
| `who_are_u.md` does not exist | Offer to run Vera in `create` mode |
| `who_are_u.md` exists | Ask the user: **reuse as-is** (skip Vera) or **refresh** (run Vera in `refresh` mode) |

Vera never runs inside the optimization loop, only before it.

---

## Conversation Coverage

1. Career history (companies, roles, scope)
2. Signature projects (real tech, scale, contribution)
3. Ways of thinking & leadership
4. Verified credentials
5. Values & motivations

---

## Output

| File | Description |
|---|---|
| `data/docs/who_are_u.md` | Confirmed candidate background, with `**Verified:**` / `**Aspirational:**` markers where the distinction matters |

---

## Runbook

[`main.md`](main.md)
