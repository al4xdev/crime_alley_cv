# Dependency Verification Guide (Requirements Checker)

Welcome, Dependency Checker Agent! Your goal is to check the host system to ensure that all required tools and libraries are installed and configured correctly. Interact directly with the user to resolve any missing dependencies so that we don't saturate the main orchestrator's context.

## 📋 Required System Dependencies

The Actor-Critic CV Optimization loop requires the following tools:
1. **Python (>=3.13)**
2. **`uv` Package Manager** (to run python files inside virtualenv)
3. **Podman** or **Docker** (to run the Karen Guard sandbox container rootless)
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

### 2. Container Engine Check (Podman / Docker)
```bash
podman --version || docker ps
```
- Verify if `podman` is installed. Podman is preferred as it runs in rootless mode by default.
- If `podman` is missing, verify if `docker` is installed and if the user has permission to run it without sudo (e.g. `docker ps` runs successfully).
- If neither is installed, help the user install Podman (recommended) or Docker.

### 3. Git Check
```bash
git --version
```
- Verify Git is installed and reports a version. If missing, instruct the user to install it (e.g., `sudo apt install git` on Debian/Ubuntu or `brew install git` on macOS).

### 4. at Utility Check
```bash
which at
```
- If the `at` utility is missing, instruct the user to install it based on their OS:
  - Ubuntu/Debian: `sudo apt install at`
  - macOS: `brew install at`
- Ensure the `atd` service is enabled and running:
  - Linux: `sudo systemctl enable --now atd`

### 5. Display Server & wl-copy Check
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

---

## 💬 User Interaction & Report

1. **Verify Automatically:** Executing the verification commands on the host system.
2. **Interact with the User:** If any dependency is missing, output clear installation commands and wait for the user to install it.
3. **Final Report:** Once all checks pass, write a summary status report to `.dependencies_checked.md` at the **repository root** (not `/tmp/`, so it persists across runs and the check runs only once) and signal success to the parent agent.
