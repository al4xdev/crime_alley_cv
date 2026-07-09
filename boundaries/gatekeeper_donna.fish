#!/usr/bin/env fish
# boundaries/gatekeeper_donna.fish — Boundary validation hook for Donna Career Coaching

if set -q BOUNDARY_REPO_ROOT
    set repo_root "$BOUNDARY_REPO_ROOT"
else
    set boundary_dir (status dirname)
    set repo_root "$boundary_dir/.."
end

set mode $argv[1]
set session_id $argv[2]

if test "$mode" = "--pre"
    # Pre-conditions:
    if test -z "$session_id"
        echo "Error [Donna boundary]: session_id is missing." >&2
        exit 1
    end
    set session_dir "/tmp/karen_guard_$session_id"
    set eval_file "$session_dir/anti_karen/karen_output.md"
    if not test -f "$eval_file"
        echo "Error [Donna boundary]: Evaluation report '$eval_file' is missing." >&2
        exit 1
    end

    if test -z "$FIT_SCORE"
        echo "Error [Donna boundary]: FIT_SCORE environment variable is missing." >&2
        exit 1
    end
    if test -z "$MIN_FIT_SCORE"
        echo "Error [Donna boundary]: MIN_FIT_SCORE environment variable is missing." >&2
        exit 1
    end

    # Build donna_input.json
    set output_dir "$session_dir/anti_karen"
    set json_input "$output_dir/donna_input.json"

    jq -n \
        --arg sid "$session_id" \
        --arg sdir "$session_dir" \
        --arg krp "$session_dir/anti_karen/karen_output.md" \
        --argjson fs "$FIT_SCORE" \
        --argjson mfs "$MIN_FIT_SCORE" \
        '{session_id: $sid, session_dir: $sdir, karen_report_path: $krp, fit_score: $fs, min_fit_score: $mfs}' \
        > "$json_input"

    # Invoke validation and rendering
    uv run python "$repo_root/harvey_guy/render_instructions.py" \
        --agent donna \
        --data-file "$json_input" \
        --template-path "$repo_root/donna_nana/main.md" \
        --output-dir "$output_dir"
    set render_status $status
    if test $render_status -ne 0
        echo "Error [Donna boundary]: Failed to validate/render instructions (exit code $render_status)." >&2
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
