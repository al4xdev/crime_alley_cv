# Job-Stack & Karen Guard

Orchestrator and evaluator of automated job applications based on a multi-agent Actor-Critic architecture.

## Multi-Agent Architecture (Actor-Critic Loop)

The project is structured as a system of autonomous agents cooperating in a continuous feedback loop to optimize and validate resumes:

1. **Harvey (Orchestrator/Context)**: Gathers candidate data, clones public repositories, researches the target company (saving details to `company_info.md`), and prepares the isolated session workspace including a protected `anti_karen/` folder.
2. **Karen Guard (Evaluator/Critic)**: Analyzes the candidate's CV against the job requirements and validates technical claims by inspecting actual code in their repositories. Highly skeptical, producing a detailed report of inconsistencies and defects (`evaluation.md`). She is prohibited from reading files inside the `anti_karen/` directory.
3. **Bill (Editor/Generator)**: Referenced as the original writer/co-creator of Batman (who was the true creative force, abbreviated `billf`), this agent consumes the original CV, job description, and Karen's defect report, rewriting the CV to address all criticisms and align the candidate's senior profile.

---

## Modules Glossary

* [Harvey (Orchestrator)](harvey_guy/README.md) - Context collection and workspace setup.
* [Karen Guard (Evaluator)](karen_guard/Readme.md) - Skeptical static validator and technical fit reporting.
* [Bill (Editor)](billf/README.md) - Automated CV review and optimization.

---

## Session and Log Architecture

On each run of the main orchestrator (`harvey_guy/main.py`), a new session with a unique identifier (UUID) is generated.

### Session Directory
A dedicated folder for the current session is created in the system's temporary directory:
`/tmp/karen_guard_<UUID>/`

### Log Location
The log file of the current run is stored inside the protected session folder:
`/tmp/karen_guard_<UUID>/anti_karen/karen_guard_core.log`

Logs contain detailed timestamps and a sequential message counter (`[count]`) for precise tracking of the pipeline execution.
