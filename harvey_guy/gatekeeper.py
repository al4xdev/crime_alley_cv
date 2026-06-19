#!/usr/bin/env python3
import argparse
import json
import re
import shutil
import sys
from pathlib import Path


def extract_score(report_content: str) -> int:
    """
    Extracts the fit score from the report content using regex pattern matching.
    """
    patterns = [
        r"(?:technical\s+)?fit\s+score\s*(?:\([^)]*\))?\s*:\s*\**(\d+)(?:/100)?\**",
        r"(?:technical\s+)?fit\s+score\s*(?:\([^)]*\))?\s*-\s*\**(\d+)(?:/100)?\**",
        r"\bscore\b\s*:\s*\**(\d+)(?:/100)?\**",
        r"\bscore\b\s*-\s*\**(\d+)(?:/100)?\**",
        r"(\d+)/100",
    ]
    
    # First search line-by-line to prevent matching unrelated numbers
    for line in report_content.splitlines():
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return int(match.group(1))
                
    # Fallback to searching the entire text
    for pattern in patterns:
        match = re.search(pattern, report_content, re.IGNORECASE)
        if match:
            return int(match.group(1))
            
    raise ValueError("Could not extract a valid fit score from the report.")


def parse_args():
    parser = argparse.ArgumentParser(description="Deterministic Gatekeeper for Actor-Critic Loop")
    parser.add_argument("--min-fit-score", type=int, required=True, help="Target minimum fit score")
    parser.add_argument("--max-loops", type=int, required=True, help="Maximum number of loops")
    parser.add_argument(
        "--current-loop", type=int, required=True, help="Current loop iteration index"
    )
    parser.add_argument(
        "--session-dir", type=str, required=True, help="Path to the session directory"
    )
    parser.add_argument("--karen-report", type=str, help="Path to the Karen report file")
    parser.add_argument("--data-dir", type=str, help="Path to the .data/docs directory")
    return parser.parse_args()


def main():
    args = parse_args()
    
    session_dir = Path(args.session_dir)
    if not session_dir.exists():
        print(f"Error: Session directory '{session_dir}' does not exist.", file=sys.stderr)
        sys.exit(3)
        
    karen_report_path = (
        Path(args.karen_report)
        if args.karen_report
        else session_dir / "anti_karen" / "karen_output.md"
    )
    
    if not karen_report_path.exists():
        print(f"Error: Karen report file '{karen_report_path}' does not exist.", file=sys.stderr)
        sys.exit(3)
        
    try:
        report_content = karen_report_path.read_text(encoding="utf-8")
        fit_score = extract_score(report_content)
    except Exception as e:
        print(f"Error: Score extraction failed. {e}", file=sys.stderr)
        sys.exit(3)
        
    # Determine repo data directory
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    data_docs_dir = (
        Path(args.data_dir)
        if args.data_dir
        else repo_root / ".data" / "docs"
    )
    
    print(f"Successfully extracted FIT_SCORE: {fit_score}")
    
    # Evaluate gatekeeper exit conditions
    if fit_score >= args.min_fit_score:
        # Success exit
        msg = (
            f"Gatekeeper: SUCCESS. Fit score {fit_score} meets or "
            f"exceeds target {args.min_fit_score}."
        )
        print(msg)
        src_cv = session_dir / "docs" / "cv.md"
        dest_cv = data_docs_dir / "cv.md"
        data_docs_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_cv, dest_cv)
        print(f"Copied final CV from {src_cv} to {dest_cv}")
        # Print status for main runbook consumption
        print(json.dumps({"status": "success", "fit_score": fit_score}))
        sys.exit(0)
        
    elif args.current_loop >= args.max_loops:
        # Max loops exit
        msg = (
            f"Gatekeeper: MAX LOOPS. Current loop index {args.current_loop} "
            f"meets or exceeds limit {args.max_loops}."
        )
        print(msg)
        src_cv = session_dir / "docs" / "cv.md"
        dest_cv = data_docs_dir / "cv.md"
        data_docs_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_cv, dest_cv)
        print(f"Copied final CV from {src_cv} to {dest_cv}")
        # Print status for main runbook consumption
        print(json.dumps({"status": "max_loops", "fit_score": fit_score}))
        sys.exit(1)
        
    else:
        # Refinement loop continues
        msg = (
            f"Gatekeeper: CONTINUE. Fit score {fit_score} is below target "
            f"{args.min_fit_score}. Loop continues."
        )
        print(msg)
        print(json.dumps({"status": "continue", "fit_score": fit_score}))
        sys.exit(2)


if __name__ == "__main__":
    main()
