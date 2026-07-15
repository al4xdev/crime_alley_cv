from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


class ProviderError(RuntimeError):
    pass


def _run(command: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=cwd)
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip()
        raise ProviderError(f"Provider command failed ({result.returncode}): {error}")
    return result.stdout


def run_prompt(provider: str, model: str, prompt: str) -> str:
    if not model.strip():
        raise ValueError("An explicit model is required")
    with tempfile.TemporaryDirectory(prefix="celestial-judge-") as working_directory:
        cwd = Path(working_directory)
        if provider == "agy":
            return _run(
                [
                    "agy",
                    "--model",
                    model,
                    "--sandbox",
                    "--print-timeout",
                    "15m",
                    "--print",
                    prompt,
                ],
                cwd=cwd,
            )
        if provider == "claude":
            environment = os.environ.copy()
            environment["DISABLE_AUTOUPDATER"] = "1"
            result = subprocess.run(
                [
                    "claude",
                    "-p",
                    "--model",
                    model,
                    "--output-format",
                    "text",
                    "--permission-mode",
                    "dontAsk",
                    "--disallowedTools",
                    "Bash",
                    "Edit",
                    "Write",
                    "Read",
                    "Glob",
                    "Grep",
                    "NotebookEdit",
                    "WebFetch",
                    "WebSearch",
                    "Agent",
                    prompt,
                ],
                capture_output=True,
                text=True,
                check=False,
                env=environment,
                cwd=cwd,
            )
            if result.returncode != 0:
                raise ProviderError(result.stderr.strip() or "Claude provider call failed")
            return result.stdout
        if provider == "codex":
            descriptor, output_name = tempfile.mkstemp(prefix="celestial-codex-", suffix=".json")
            os.close(descriptor)
            output = Path(output_name)
            try:
                _run(
                    [
                        "codex",
                        "exec",
                        "--ephemeral",
                        "--skip-git-repo-check",
                        "--sandbox",
                        "read-only",
                        "--ask-for-approval",
                        "never",
                        "--model",
                        model,
                        "--output-last-message",
                        str(output),
                        prompt,
                    ],
                    cwd=cwd,
                )
                return output.read_text(encoding="utf-8")
            finally:
                output.unlink(missing_ok=True)
    raise ValueError(f"Unsupported provider: {provider}")


def assert_model_capability(provider: str) -> None:
    binary = {"agy": "agy", "claude": "claude", "codex": "codex"}.get(provider)
    if binary is None:
        raise ValueError(f"Unsupported provider: {provider}")
    command = [binary, "--help"] if provider != "codex" else [binary, "exec", "--help"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    help_text = result.stdout + result.stderr
    if result.returncode != 0 or "--model" not in help_text:
        raise ProviderError(f"{provider} does not expose the required --model capability")
