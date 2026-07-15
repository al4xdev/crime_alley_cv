from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import generate_baseline, plan_capture, run_benchmark
from .capture import verify_frozen_case
from .labels import export_blind_tasks, import_label
from .metrics import build_report
from .provider import assert_model_capability


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Content-only The Celestial benchmark")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "baseline", "judge"):
        command = commands.add_parser(name)
        command.add_argument("--capture", required=True)
    commands.choices["baseline"].add_argument("--accept-plan", required=True)
    commands.choices["judge"].add_argument("--accept-plan", required=True)
    report = commands.add_parser("report")
    report.add_argument("--benchmark", required=True, type=Path)
    export = commands.add_parser("export-labels")
    export.add_argument("--benchmark", required=True, type=Path)
    export.add_argument("--output", required=True, type=Path)
    import_command = commands.add_parser("import-label")
    import_command.add_argument("path", type=Path)
    verify = commands.add_parser("verify-case")
    verify.add_argument("case_id")
    capability = commands.add_parser("capability")
    capability.add_argument("--provider", choices=("agy", "claude", "codex"), required=True)
    capability.add_argument("--model", required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "plan":
        value = plan_capture(args.capture)
    elif args.command == "baseline":
        value = {"baseline": str(generate_baseline(args.capture, args.accept_plan))}
    elif args.command == "judge":
        value = {"benchmark": str(run_benchmark(args.capture, plan_digest=args.accept_plan))}
    elif args.command == "report":
        value = build_report(args.benchmark)
    elif args.command == "export-labels":
        value = {"output": str(export_blind_tasks(args.benchmark, args.output))}
    elif args.command == "import-label":
        value = {"label": str(import_label(args.path))}
    elif args.command == "verify-case":
        value = verify_frozen_case(args.case_id)
    else:
        assert_model_capability(args.provider, args.model)
        value = {"provider": args.provider, "model": args.model, "no_tools": True}
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
