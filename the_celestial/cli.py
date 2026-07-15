from __future__ import annotations

import argparse
import json
from pathlib import Path

from .benchmark import generate_baseline, plan_capture, run_benchmark
from .capture import data_root, verify_frozen_case
from .io import read_json_object
from .labels import export_blind_tasks, import_label
from .metrics import build_report


def _request(capture_id: str) -> dict[str, object]:
    return read_json_object(data_root() / "captures" / capture_id / "request.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Content-only The Celestial benchmark")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "baseline", "judge"):
        command = commands.add_parser(name)
        command.add_argument("--capture", required=True)
    judge = commands.choices["judge"]
    judge.add_argument("--confirm-high-quota", action="store_true")
    report = commands.add_parser("report")
    report.add_argument("--benchmark", required=True, type=Path)
    export = commands.add_parser("export-labels")
    export.add_argument("--benchmark", required=True, type=Path)
    export.add_argument("--output", required=True, type=Path)
    import_command = commands.add_parser("import-label")
    import_command.add_argument("path", type=Path)
    verify = commands.add_parser("verify-case")
    verify.add_argument("case_id")
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "plan":
        value = plan_capture(args.capture)
    elif args.command == "baseline":
        request = _request(args.capture)
        if not request.get("celestial_requested"):
            raise SystemExit("The Celestial was not enabled for this capture")
        value = {
            "baseline": str(
                generate_baseline(
                    args.capture,
                    str(request["subject_provider"]),
                    str(request["subject_model"]),
                )
            )
        }
    elif args.command == "judge":
        if not args.confirm_high_quota:
            raise SystemExit("Refusing model calls without --confirm-high-quota")
        request = _request(args.capture)
        value = {
            "benchmark": str(
                run_benchmark(
                    args.capture,
                    judge_provider=str(request["judge_provider"]),
                    judge_model=str(request["judge_model"]),
                )
            )
        }
    elif args.command == "report":
        value = build_report(args.benchmark)
    elif args.command == "export-labels":
        value = {"output": str(export_blind_tasks(args.benchmark, args.output))}
    elif args.command == "import-label":
        value = {"label": str(import_label(args.path))}
    else:
        value = verify_frozen_case(args.case_id)
    print(json.dumps(value, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
