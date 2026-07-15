from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class ProviderError(RuntimeError):
    pass


class ProviderCapabilityError(ProviderError):
    pass


def validate_exact_model(provider: str, model: str) -> None:
    patterns = {
        "claude": r"^claude-[a-z0-9-]+-[0-9]{8}$",
        "codex": r"^gpt-[0-9]+(?:\.[0-9]+)+(?:-[a-z0-9.-]+)?$",
    }
    pattern = patterns.get(provider)
    if pattern is None:
        raise ProviderCapabilityError(
            f"{provider} is blocked for Celestial calls until no-tool enforcement is verifiable"
        )
    if re.fullmatch(pattern, model) is None:
        raise ValueError(f"{provider} requires a versioned model ID, not an alias: {model!r}")


def _run(command: list[str], *, cwd: Path) -> str:
    result = subprocess.run(command, capture_output=True, text=True, check=False, cwd=cwd)
    if result.returncode != 0:
        error = result.stderr.strip() or result.stdout.strip()
        raise ProviderError(f"Provider command failed ({result.returncode}): {error}")
    return result.stdout


def assert_model_capability(provider: str, model: str) -> None:
    validate_exact_model(provider, model)
    binary = "claude" if provider == "claude" else "codex"
    command = [binary, "--help"] if provider == "claude" else [binary, "exec", "--help"]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    text = result.stdout + result.stderr
    required = (
        (
            "--model",
            "--tools",
            "--safe-mode",
            "--disable-slash-commands",
            "--no-session-persistence",
            "--strict-mcp-config",
            "--json-schema",
        )
        if provider == "claude"
        else (
            "--model",
            "--disable",
            "--strict-config",
            "--sandbox",
            "--ignore-user-config",
            "--ignore-rules",
            "--ephemeral",
            "--output-schema",
        )
    )
    if result.returncode != 0 or any(flag not in text for flag in required):
        raise ProviderCapabilityError(f"{provider} lacks required model/no-tool CLI capabilities")


def run_prompt(
    provider: str,
    model: str,
    prompt: str,
    *,
    schema: dict[str, Any] | None = None,
) -> str:
    validate_exact_model(provider, model)
    with tempfile.TemporaryDirectory(prefix="celestial-judge-") as working_directory:
        cwd = Path(working_directory)
        schema_path = cwd / "schema.json"
        if schema is not None:
            schema_path.write_text(json.dumps(schema), encoding="utf-8")
        if provider == "claude":
            environment = os.environ.copy()
            environment["DISABLE_AUTOUPDATER"] = "1"
            command = [
                "claude",
                "-p",
                "--model",
                model,
                "--output-format",
                "text",
                "--permission-mode",
                "dontAsk",
                "--tools",
                "",
                "--safe-mode",
                "--disable-slash-commands",
                "--no-session-persistence",
                "--strict-mcp-config",
                "--mcp-config",
                '{"mcpServers":{}}',
            ]
            if schema is not None:
                command.extend(("--json-schema", json.dumps(schema, separators=(",", ":"))))
            command.append(prompt)
            result = subprocess.run(
                command,
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
            output = cwd / "last-message.json"
            command = [
                "codex",
                "exec",
                "--ephemeral",
                "--skip-git-repo-check",
                "--ignore-user-config",
                "--ignore-rules",
                "--strict-config",
                "--sandbox",
                "read-only",
                "--disable",
                "shell_tool",
                "--disable",
                "unified_exec",
                "-c",
                'web_search="disabled"',
                "--model",
                model,
                "--output-last-message",
                str(output),
            ]
            if schema is not None:
                command.extend(("--output-schema", str(schema_path)))
            command.append(prompt)
            _run(command, cwd=cwd)
            return output.read_text(encoding="utf-8")
    raise ProviderCapabilityError(f"Unsupported Celestial provider: {provider}")
