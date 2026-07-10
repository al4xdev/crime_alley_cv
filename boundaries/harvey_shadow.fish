#!/usr/bin/env fish
# boundaries/harvey_shadow.fish — Boundary validation hook for Harvey Shadow

if set -q BOUNDARY_REPO_ROOT
    set repo_root "$BOUNDARY_REPO_ROOT"
else
    set boundary_dir (status dirname)
    set repo_root "$boundary_dir/.."
end

set mode $argv[1]
set session_id $argv[2]

set -g BOUNDARY_NAME "harvey_shadow.fish"
source "$repo_root/boundaries/audit_logger.fish"

if test "$mode" = "--pre"
    # Pre-conditions:
    if test -z "$session_id"
        echo "Error [shadow boundary]: session_id is missing." >&2
        exit 1
    end
    set session_dir "/tmp/karen_guard_$session_id"
    if not test -d "$session_dir"
        echo "Error [shadow boundary]: Session directory '$session_dir' does not exist." >&2
        exit 1
    end
    # Build shadow_input.json
    set output_dir "$session_dir/anti_karen"
    set json_input "$output_dir/shadow_input.json"

    jq -n \
        --arg sid "$session_id" \
        --arg sdir "$session_dir" \
        '{session_id: $sid, session_dir: $sdir}' \
        > "$json_input"

    # Invoke validation and rendering
    uv run python "$repo_root/harvey_guy/render_instructions.py" \
        --agent shadow \
        --data-file "$json_input" \
        --template-path "$repo_root/harvey_guy/shadow.md" \
        --output-dir "$output_dir"
    set render_status $status
    if test $render_status -ne 0
        echo "Error [shadow boundary]: Failed to validate/render instructions (exit code $render_status)." >&2
        exit 1
    end

    exit 0

else if test "$mode" = "--post"
    # Post-conditions:
    set session_dir "/tmp/karen_guard_$session_id"
    
    # 1. Verify company_info.md exists and is non-empty
    set comp_info "$session_dir/company_info.md"
    if not test -f "$comp_info"
        echo "Error [shadow boundary]: Missing '$comp_info'." >&2
        exit 1
    end
    set size (stat -c %s "$comp_info" 2>/dev/null; or stat -f %z "$comp_info" 2>/dev/null; or echo 0)
    if test "$size" -lt 10
        echo "Error [shadow boundary]: '$comp_info' is empty or too small ($size bytes)." >&2
        exit 1
    end

    # 2. Check repos expected count vs cloned repos count
    set count_file "$session_dir/repos_expected_count.txt"
    if test -f "$count_file"
        set expected_count (cat "$count_file" | string trim)
        if string match -r '^\d+$' "$expected_count" >/dev/null
            set actual_count (find "$session_dir/repos" -mindepth 1 -maxdepth 1 -type d | wc -l)
            if test "$actual_count" -ne "$expected_count"
                # Check if there is a warning file or log
                set warnings_file "$session_dir/anti_karen/clone_warnings.txt"
                if test -s "$warnings_file"
                    echo "Warning [shadow boundary]: Repository count mismatch (Expected: $expected_count, Got: $actual_count). Warning file found."
                else
                    echo "Error [shadow boundary]: Repository count mismatch (Expected: $expected_count, Got: $actual_count) without clone_warnings.txt." >&2
                    exit 1
                end
            end
        else
            echo "Warning [shadow boundary]: Expected count in '$count_file' is not a valid number: '$expected_count'."
        end
    end

    exit 0
else
    echo "Usage: boundaries/harvey_shadow.fish [--pre|--post] [session_id]" >&2
    exit 2
end
