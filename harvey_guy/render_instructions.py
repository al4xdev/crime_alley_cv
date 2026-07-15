from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jinja2 import Environment, StrictUndefined
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .io import atomic_write_text


class ContractModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class ShadowInput(ContractModel):
    session_id: str = Field(min_length=1)
    session_dir: str = Field(min_length=1)


class BillInput(ContractModel):
    session_id: str = Field(min_length=1)
    session_dir: str = Field(min_length=1)
    karen_report_path: str = Field(min_length=1)
    candidate_background_path: str | None = None


class DonnaInput(ContractModel):
    session_id: str = Field(min_length=1)
    session_dir: str = Field(min_length=1)
    karen_report_path: str = Field(min_length=1)
    action_plan_path: str = Field(min_length=1)
    fit_score: int = Field(ge=0, le=100)
    min_fit_score: int = Field(ge=0, le=100)


MODELS: dict[str, type[ContractModel]] = {
    "shadow": ShadowInput,
    "bill": BillInput,
    "donna": DonnaInput,
}

PROMPTS = {
    "shadow": """Welcome, Harvey Shadow! Read and follow: {{ instructions_path }}

Inputs:
- SESSION_ID: {{ session_id }}
- SESSION_DIR: {{ session_dir }}

Validated JSON: {{ input_json_path }}
""",
    "bill": """Welcome, Bill! Read and follow: {{ instructions_path }}

Inputs:
- SESSION_ID: {{ session_id }}
- SESSION_DIR: {{ session_dir }}
- KAREN_REPORT_PATH: {{ karen_report_path }}
- CANDIDATE_BACKGROUND_PATH: {{ candidate_background_path }}

Validated JSON: {{ input_json_path }}
""",
    "donna": """Welcome, Donna! Read and follow: {{ instructions_path }}

Inputs:
- SESSION_ID: {{ session_id }}
- SESSION_DIR: {{ session_dir }}
- KAREN_REPORT_PATH: {{ karen_report_path }}
- ACTION_PLAN_PATH: {{ action_plan_path }}
- FIT_SCORE: {{ fit_score }}
- MIN_FIT_SCORE: {{ min_fit_score }}

Validated JSON: {{ input_json_path }}
""",
}

JINJA = Environment(undefined=StrictUndefined, autoescape=False, keep_trailing_newline=True)


@dataclass(frozen=True, slots=True)
class RenderedContract:
    input_json: Path
    instructions: Path
    prompt: Path


def render_agent(
    agent: str,
    data: dict[str, Any],
    template_path: Path,
    output_dir: Path,
) -> RenderedContract:
    try:
        model_class = MODELS[agent]
    except KeyError as exc:
        raise ValueError(f"Unknown agent: {agent}") from exc
    if not template_path.is_file():
        raise FileNotFoundError(template_path)

    model = model_class.model_validate(data)
    context = model.model_dump()
    output_dir.mkdir(parents=True, exist_ok=True)

    input_json = output_dir / f"{agent}_input.json"
    instructions = output_dir / f"{agent}_instructions.md"
    prompt = output_dir / f"{agent}.prompt"

    atomic_write_text(input_json, model.model_dump_json(indent=2) + "\n")
    template = JINJA.from_string(template_path.read_text(encoding="utf-8"))
    atomic_write_text(instructions, template.render(**context))

    prompt_context = {
        **context,
        "instructions_path": str(instructions),
        "input_json_path": str(input_json),
    }
    prompt_template = JINJA.from_string(PROMPTS[agent])
    atomic_write_text(prompt, prompt_template.render(**prompt_context))
    return RenderedContract(input_json=input_json, instructions=instructions, prompt=prompt)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a validated agent contract")
    parser.add_argument("--agent", required=True, choices=sorted(MODELS))
    parser.add_argument("--data-file", required=True, type=Path)
    parser.add_argument("--template-path", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    try:
        data = json.loads(args.data_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Data file must contain a JSON object")
        render_agent(args.agent, data, args.template_path, args.output_dir)
    except (OSError, ValueError, ValidationError) as exc:
        print(f"Contract rendering failed for {args.agent}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Contract rendered for {args.agent}.")


if __name__ == "__main__":
    main()
