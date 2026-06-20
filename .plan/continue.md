# Continuation Guide — Resume Loop on New Machine

This file contains the status and step-by-step instructions to resume the Crime Alley CV Optimization loop on a new computer.

---

## 📍 Current Project Status

- **Fixed Host Token Overwrite Bug**: A bug in [run.sh](file:///home/alex/git/my/meta_2028/karen_guard/run.sh) was fixed. Previously, when the pytest unit tests ran on the host, the fallback command `getent passwd` resolved `/home/alex` instead of respecting the mocked `$HOME` path. This resulted in the host's actual oauth token (`~/.gemini/antigravity-cli/antigravity-oauth-token`) being overwritten with `"mock-oauth-token"`. The bug is now fixed (by preferring `$HOME` env var), meaning your host tokens won't be corrupted by tests in the future.
- **Clean Workspace**: Old runs were backed up and renamed to [.runs/.bak_20260620_152408](file:///home/alex/git/my/meta_2028/.runs/.bak_20260620_152408) to prevent loops from colliding or using old data.
- **Watchdog Script**: A local watchdog script is prepared at [.plan/watchdog.fish](file:///home/alex/git/my/meta_2028/.plan/watchdog.fish) to monitor loop checkpoints and logs.

---

## 🚀 Steps to Resume Execution on the New Machine

Follow these steps once you clone the repository on your new computer:

### 1. Prerequisite: Authenticate `agy` on the Host
Because the oauth token on the host was overwritten by the tests, you will need to authenticate the Antigravity CLI. Run the following command on your new host terminal:
```bash
agy
```
Follow the prompts to sign in with your Google Account. This will populate your local `~/.gemini/` directory with a valid credential token.

### 2. Start the Orchestrator Container
Start the container build and interactive runtime by running:
```bash
./start.sh
```
This builds `crime_alley_pipeline` and starts the container in interactive mode using the `fish` shell.

### 3. Run the Loop Orchestrator
Inside the container's interactive shell, launch the orchestrator script:
```fish
uv run python harvey_guy/main.py
```
* **Variables**: When prompted, set your desired loop values:
  * `MAX_LOOPS` (default: 3)
  * `MIN_FIT_SCORE` (default: 80)
  * `JOB_DESCRIPTION_RAW` (paste description)
  * `KAREN_READS_BACKGROUND` (yes / no)

### 4. Interactive Evaluator Login (If prompted)
When the orchestrator reaches the **Step 2: Skeptical Auditing (Karen Guard)** phase, it will run the nested container.
- If it successfully reads your host credentials from `/root/.gemini` (mounted automatically by `start.sh`), the audit runs in the background.
- If it needs login, the terminal will display the interactive `agy` login prompt. Simply follow the options on-screen to authenticate it.

### 5. Monitor Loop Progress
From a separate terminal on your host machine, you can run the watchdog script to check the loop's checkpoints, session files, and logs:
```bash
./.plan/watchdog.fish
```
You can also ask your Antigravity agent on the new machine to schedule a periodic watchdog task (every 2 minutes) to keep you updated.
