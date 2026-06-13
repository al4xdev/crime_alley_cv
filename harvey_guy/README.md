# Harvey (Orchestrator)

Module responsible for the initial orchestration of the pipeline, local data ingestion, and candidate context collection.

## Features

1. **Session Management**: Creates the temporary execution directory `/tmp/karen_guard_<UUID>/` and initializes detailed pipeline logging.
2. **Document Ingestion**: Copies local resume, briefing, and job description files from `data/docs/` to the session folder.
3. **Repository Mapping**: Detects the candidate's GitHub username from the local git configuration and queries the GitHub API to fetch public repositories.
4. **Cloning and Workspace**: Clones the public repositories into `/tmp/karen_guard_<UUID>/repos/` for subsequent code analysis.
5. **Session Output**: Prints the session UUID at the end to allow for shell command piping.

## Execution

The main entrypoint of Harvey can be executed directly using Python:

```bash
uv run python harvey_guy/main.py
```
