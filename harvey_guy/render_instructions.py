import argparse
import json
import sys
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, StrictStr, StrictInt, ValidationError
from jinja2 import Template

class ShadowInput(BaseModel):
    model_config = ConfigDict(strict=True)
    session_id: StrictStr = Field(..., min_length=1)
    session_dir: StrictStr = Field(..., min_length=1)

class BillInput(BaseModel):
    model_config = ConfigDict(strict=True)
    session_id: StrictStr = Field(..., min_length=1)
    session_dir: StrictStr = Field(..., min_length=1)
    karen_report_path: StrictStr = Field(..., min_length=1)
    candidate_background_path: Optional[StrictStr] = None

class DonnaInput(BaseModel):
    model_config = ConfigDict(strict=True)
    session_id: StrictStr = Field(..., min_length=1)
    session_dir: StrictStr = Field(..., min_length=1)
    karen_report_path: StrictStr = Field(..., min_length=1)
    fit_score: StrictInt = Field(..., ge=0, le=100)
    min_fit_score: StrictInt = Field(..., ge=0, le=100)

MODELS = {
    "shadow": ShadowInput,
    "bill": BillInput,
    "donna": DonnaInput,
}

PROMPTS = {
    "shadow": """Welcome, Harvey Shadow! You are the execution agent. Please read and follow the instructions defined in the file: {{ instructions_path }}

Your input parameters are:
- SESSION_ID: {{ session_id }}
- SESSION_DIR: {{ session_dir }}

You can also read the JSON configuration at: {{ input_json_path }}
""",
    "bill": """Welcome, Bill! You are the editor agent. Please read and follow the instructions defined in the file: {{ instructions_path }}

Your input parameters are:
- SESSION_ID: {{ session_id }}
- SESSION_DIR: {{ session_dir }}
- KAREN_REPORT_PATH: {{ karen_report_path }}
- CANDIDATE_BACKGROUND_PATH: {{ candidate_background_path }}

You can also read the JSON configuration at: {{ input_json_path }}
""",
    "donna": """Welcome, Donna! You are the coaching agent. Please read and follow the instructions defined in the file: {{ instructions_path }}

Your input parameters are:
- SESSION_ID: {{ session_id }}
- SESSION_DIR: {{ session_dir }}
- KAREN_REPORT_PATH: {{ karen_report_path }}
- FIT_SCORE: {{ fit_score }}
- MIN_FIT_SCORE: {{ min_fit_score }}

You can also read the JSON configuration at: {{ input_json_path }}
"""
}

def main():
    parser = argparse.ArgumentParser(description="Render deterministic contracts and instructions")
    parser.add_argument("--agent", required=True, choices=list(MODELS.keys()), help="Agent name")
    parser.add_argument("--data-file", required=True, help="Path to JSON data file")
    parser.add_argument("--template-path", required=True, help="Path to the template markdown file")
    parser.add_argument("--output-dir", required=True, help="Directory to output rendered files")
    args = parser.parse_args()

    data_file_path = Path(args.data_file)
    if not data_file_path.exists():
        print(f"Error: Data file not found at '{data_file_path}'", file=sys.stderr)
        sys.exit(1)

    try:
        data_dict = json.loads(data_file_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error parsing JSON data file: {e}", file=sys.stderr)
        sys.exit(1)

    model_class = MODELS[args.agent]
    try:
        model = model_class(**data_dict)
    except ValidationError as e:
        print(f"Pydantic validation failed for {args.agent}: {e}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save validated input JSON
    json_output_path = output_dir / f"{args.agent}_input.json"
    json_output_path.write_text(model.model_dump_json(indent=2), encoding="utf-8")

    # Render template
    template_file = Path(args.template_path)
    if not template_file.exists():
        print(f"Error: Template not found at '{template_file}'", file=sys.stderr)
        sys.exit(1)

    template_content = template_file.read_text(encoding="utf-8")
    context = model.model_dump()
    
    try:
        template = Template(template_content)
        rendered_content = template.render(**context)
    except Exception as e:
        print(f"Error rendering Jinja2 template: {e}", file=sys.stderr)
        sys.exit(1)

    instructions_path = output_dir / f"{args.agent}_instructions.md"
    instructions_path.write_text(rendered_content, encoding="utf-8")

    # Generate prompt file (.prompt)
    prompt_template_content = PROMPTS[args.agent]
    prompt_context = context.copy()
    prompt_context["instructions_path"] = str(instructions_path)
    prompt_context["input_json_path"] = str(json_output_path)

    try:
        prompt_template = Template(prompt_template_content)
        rendered_prompt = prompt_template.render(**prompt_context)
    except Exception as e:
        print(f"Error rendering prompt template: {e}", file=sys.stderr)
        sys.exit(1)

    prompt_path = output_dir / f"{args.agent}.prompt"
    prompt_path.write_text(rendered_prompt, encoding="utf-8")

    print(f"Deterministic contract and prompt rendered successfully for {args.agent}.")
    sys.exit(0)

if __name__ == "__main__":
    main()
