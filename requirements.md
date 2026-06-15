# Dependency Verification Guide (Requirements Checker)

Welcome, Dependency Checker Agent! Your goal is to check the host system to ensure that all required tools and libraries are installed and configured correctly. Interact directly with the user to resolve any missing dependencies so that we don't saturate the main orchestrator's context.

## 📋 Required System Dependencies

The Actor-Critic CV Optimization loop requires the following tools:
1. **Python (>=3.13)**
2. **`uv` Package Manager** (to run python files inside virtualenv)
3. **Docker** (and permissions to run docker containers without sudo)
4. **`at` command-line utility** (for long-running task watchdog checks)
5. **Git** (for cloning public repositories)
6. **Display Server clipboard tools** (like `wl-clipboard` for `wl-copy` if Wayland display server is active)

---

## 🛠️ Step-by-Step Verification Instructions

Run the following commands on the host machine to check each dependency:

### 1. Python & uv Version Check
```bash
python --version
uv --version
```
- Verify Python version is `3.13` or greater.
- If `uv` is not installed, instruct the user to install it (e.g., using `curl -LsSf https://astral.sh/uv/install.sh | sh` or standard package manager).

### 2. Docker & Permission Check
```bash
docker ps
```
- If this command fails or returns a permission error, check if the user is in the `docker` group or run it via `sg docker -c "docker ps"`.
- If Docker is not installed or the user lacks permissions, help them install Docker and add their user to the `docker` group (`sudo usermod -aG docker $USER` followed by shell re-entry).

### 3. at Utility Check
```bash
which at
```
- If the `at` utility is missing, instruct the user to install it based on their OS:
  - Ubuntu/Debian: `sudo apt install at`
  - macOS: `brew install at`
- Ensure the `atd` service is enabled and running:
  - Linux: `sudo systemctl enable --now atd`

### 4. Display Server & wl-copy Check
- Check if Wayland is used:
```bash
echo $WAYLAND_DISPLAY
```
- If Wayland is active, verify that `wl-copy` is installed:
```bash
which wl-copy
```
- If Wayland is active but `wl-copy` is missing, instruct the user to install it (e.g., `sudo apt install wl-clipboard`).

---

## 💬 User Interaction & Report

1. **Verify Automatically:** Executing the verification commands on the host system.
2. **Interact with the User:** If any dependency is missing, output clear installation commands and wait for the user to install it.
3. **Final Report:** Once all checks pass, write a summary status report to `/tmp/dependencies_checked.md` and signal success to the parent agent.
