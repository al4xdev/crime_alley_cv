# Karen Guard & Job-Stack — Backlog

> Single project planning document.
> What is not implemented lives here.

---

## Target Architecture (Simplified)

```
meta_2028/
├── docs/                        ← briefing.md, cv_base.md and retrospects
├── repos/                       ← clones/copies of public repositories
└── karen_guard/
    ├── Dockerfile               ← defines the isolated environment
    ├── run.sh                   ← script to run container with volumes mounted
    └── evaluator.py             ← evaluator (Python script calling LLM APIs)
```

---

## Simplified Workflow (Initial Focus)

```
1. Prepare Karen Guard's Docker container
2. Run the container interactively/actively
3. Enter the container with the user to test and validate authentication
4. Run evaluation targeting local repos mounted as volumes
```

---

## Task Backlog

### Phase 1: Karen Guard & Docker Environment (High Priority)
- [ ] Create initial Karen Guard `Dockerfile` (Python + necessary dependencies)
- [ ] Create `run.sh` script for building and interactive execution (mounting volumes for repos and credentials)
- [ ] Test and validate authentication (interactive exploration of Gemini/Claude inside Docker)
- [ ] Implement basic evaluation script (`evaluator.py`) running inside the container

### Phase 2: Workspace Structure and Integration
- [ ] Create project folder structure (`docs/`, `repos/`)
- [ ] Organize workspace mounting workflow in `/tmp/karen_guard_<timestamp>/`
- [ ] Implement automatic generation of the evaluation report (`evaluation.md`)
- [ ] Clean up host `/tmp/` pollution by ensuring child run logs/errors (Harvey, Karen, Bill) are saved exclusively inside the session directory `/tmp/karen_guard_$SESSION_ID/`.

### Phase 3: CV Adaptation and MCP
- [ ] Implement CV adaptation script/CLI
- [ ] Create context MCP server to serve `docs/` to Antigravity CLI on the host

---

## Out of Scope (Decided)

- **CV Anonymization**: Removed from scope for technical simplification and pure focus on container isolation.
- **LinkedIn/Browser Automation**: Manual curation only.