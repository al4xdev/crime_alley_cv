# Quiet launcher UI

## Goal

Make `./start.sh` pleasant by default in an interactive terminal while preserving the complete
Docker/provider output behind `-v` and `--verbose`.

## Behavior

- Accept `-v|--verbose` alongside the existing `--agent` and `--shell` options.
- Use the compact UI only when stdout/stderr are attached to a TTY and verbose mode is off.
- Keep non-interactive runs verbose so CI logs remain complete and deterministic.
- Show one status line per expensive stage, including elapsed time:
  - global orchestrator image;
  - Celestial baseline/judge image(s);
  - provider capability checks;
  - pipeline container startup.
- Rotate deliberately cheesy Crime Alley messages while a stage runs, for example:
  - `Alfred is warming the Docker cache...`
  - `Polishing the Bat-Signal...`
  - `Asking Gotham's containers to cooperate...`
  - `Counting tokens in the shadows...`
- Never hide prompts, quota warnings, authentication errors, benchmark confirmation, or agent
  conversation output.
- Capture suppressed build/capability output in one `/tmp/crime-alley-start.<pid>.log` file.
- On failure, stop the status display, print the failing stage, show the last useful log lines, and
  preserve the full `/tmp` log path. On success, print a compact completion marker and duration.
- Honor `NO_COLOR`; use plain status messages when terminal control sequences are unavailable.

## Implementation

- Extend option parsing and usage text with `-v|--verbose`.
- Add one command wrapper that either executes directly in verbose/non-TTY mode or redirects to the
  launcher log while a low-frequency status process updates the terminal.
- Route Docker builds and Celestial capability checks through the wrapper. Keep interactive Docker
  runs attached directly to the terminal.
- Ensure the background status process uses `sleep`, exits when the command completes, and is
  cleaned up by a trap on interruption.

## Tests

- Numeric/mnemonic agent shortcuts remain unchanged.
- `-v` and `--verbose` expose raw mock-Docker output.
- Default interactive mode shows stages and hides successful raw build output.
- Non-TTY mode remains verbose.
- A failed wrapped command reports its stage, log tail, full log path, and original exit code.
- `NO_COLOR=1` produces no ANSI sequences.
- `bash -n`, focused launcher tests, Ruff, and the full pytest suite pass.

## Constraint

Do not implement or modify `start.sh` until the currently active user run has finished.
