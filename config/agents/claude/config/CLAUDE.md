# Crime Alley agent preferences

- Treat every session as a clean slate. Do not create or consume persistent memory files.
- Follow the active repository runbook and its deterministic state machine exactly.
- Use Fish syntax for commands shown to the user and use `uv` for Python work.
- Prefer moving cleanup targets to `/tmp` or using a `.bak` suffix instead of permanent deletion.
- Stop after two repetitions of the same failed approach and report the concrete blocker.
- Never weaken container, credential, guard, or audit boundaries to make a task pass.
