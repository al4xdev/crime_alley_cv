#!/usr/bin/env fish
# boundaries/harvey_shadow.fish — Boundary validation hook for Harvey Shadow

set mode $argv[1]
set session_id $argv[2]

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
                if test -f "$warnings_file"
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
