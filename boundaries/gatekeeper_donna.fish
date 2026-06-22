#!/usr/bin/env fish
# boundaries/gatekeeper_donna.fish — Boundary validation hook for Donna Career Coaching

set mode $argv[1]
set session_id $argv[2]

if test "$mode" = "--pre"
    # Pre-conditions:
    if test -z "$session_id"
        echo "Error [Donna boundary]: session_id is missing." >&2
        exit 1
    end
    set session_dir "/tmp/karen_guard_$session_id"
    set eval_file "$session_dir/anti_karen/evaluation.md"
    if not test -f "$eval_file"
        echo "Error [Donna boundary]: Evaluation report '$eval_file' is missing." >&2
        exit 1
    end
    exit 0

else if test "$mode" = "--post"
    # Post-conditions:
    set plan_file ".data/docs/action_plan.md"
    if not test -f "$plan_file"
        echo "Error [Donna boundary]: Career Action Plan '$plan_file' was not generated." >&2
        exit 1
    end

    set size (stat -c %s "$plan_file" 2>/dev/null; or stat -f %z "$plan_file" 2>/dev/null; or echo 0)
    if test "$size" -lt 100
        echo "Error [Donna boundary]: Career Action Plan is empty or too small ($size bytes)." >&2
        exit 1
    end

    # Check it contains markdown formatting (e.g. headers)
    if not grep -q "^#" "$plan_file"
        echo "Error [Donna boundary]: Career Action Plan does not seem to contain Markdown formatting." >&2
        exit 1
    end

    exit 0
else
    echo "Usage: boundaries/gatekeeper_donna.fish [--pre|--post] [session_id]" >&2
    exit 2
end
