#!/usr/bin/env fish
# boundaries/harvey_setup.fish — Boundary validation hook for Harvey Setup

set mode $argv[1]
set session_id $argv[2]

if test "$mode" = "--pre"
    # Pre-conditions:
    # 1. Check cv.md and job.md exist and are non-empty
    for doc in cv.md job.md
        set path ".data/docs/$doc"
        if not test -f "$path"
            echo "Error [setup boundary]: Missing document '$path'." >&2
            exit 1
        end
        set size (stat -c %s "$path" 2>/dev/null; or stat -f %z "$path" 2>/dev/null; or echo 0)
        if test "$size" -lt 10
            echo "Error [setup boundary]: Document '$path' is empty or too small ($size bytes)." >&2
            exit 1
        end
    end

    # 2. Check first line of job.md matches `# <Cargo> — <Empresa>`
    set first_line (head -n 1 ".data/docs/job.md")
    if not string match -r '^# .+\s+—\s+.+$' "$first_line" >/dev/null
        echo "Error [setup boundary]: job.md first line must match '# <Cargo> — <Empresa>' format. Found: '$first_line'" >&2
        exit 1
    end

    # 3. Check loop configuration variables (if exported to env)
    if test -n "$MAX_LOOPS"
        if not string match -r '^\d+$' "$MAX_LOOPS" >/dev/null
            echo "Error [setup boundary]: MAX_LOOPS must be an integer. Found: '$MAX_LOOPS'" >&2
            exit 1
        end
    end
    if test -n "$MIN_FIT_SCORE"
        if not string match -r '^\d+$' "$MIN_FIT_SCORE" >/dev/null
            echo "Error [setup boundary]: MIN_FIT_SCORE must be an integer. Found: '$MIN_FIT_SCORE'" >&2
            exit 1
        end
    end

    # 4. Check KAREN_READS_BACKGROUND
    if test -n "$KAREN_READS_BACKGROUND"
        if not test "$KAREN_READS_BACKGROUND" = "yes" -o "$KAREN_READS_BACKGROUND" = "no"
            echo "Error [setup boundary]: KAREN_READS_BACKGROUND must be 'yes' or 'no'. Found: '$KAREN_READS_BACKGROUND'" >&2
            exit 1
        end
    end

    exit 0

else if test "$mode" = "--post"
    # Post-conditions:
    if test -z "$session_id"
        echo "Error [setup boundary]: session_id argument is missing for --post validation." >&2
        exit 1
    end

    set session_dir "/tmp/karen_guard_$session_id"
    if not test -d "$session_dir"
        echo "Error [setup boundary]: Session directory '$session_dir' was not created." >&2
        exit 1
    end

    # Validate structure
    for subdir in docs repos anti_karen
        if not test -d "$session_dir/$subdir"
            echo "Error [setup boundary]: Missing subdirectory '$session_dir/$subdir'." >&2
            exit 1
        end
    end

    # Check copied files
    for doc in cv.md job.md
        if not test -f "$session_dir/docs/$doc"
            echo "Error [setup boundary]: File '$doc' was not copied to '$session_dir/docs/'." >&2
            exit 1
        end
    end

    # Routing validation for who_are_u.md
    set bg_source ".data/docs/who_are_u.md"
    if test -f "$bg_source"
        if test "$KAREN_READS_BACKGROUND" = "no"
            if not test -f "$session_dir/anti_karen/who_are_u.md"
                echo "Error [setup boundary]: KAREN_READS_BACKGROUND is 'no', but who_are_u.md was not routed to '$session_dir/anti_karen/'." >&2
                exit 1
            end
            if test -f "$session_dir/docs/who_are_u.md"
                echo "Error [setup boundary]: KAREN_READS_BACKGROUND is 'no', but who_are_u.md leaked into '$session_dir/docs/'." >&2
                exit 1
            end
        else
            # Default to yes/unset
            if not test -f "$session_dir/docs/who_are_u.md"
                echo "Error [setup boundary]: KAREN_READS_BACKGROUND is 'yes', but who_are_u.md was not routed to '$session_dir/docs/'." >&2
                exit 1
            end
            if test -f "$session_dir/anti_karen/who_are_u.md"
                echo "Error [setup boundary]: KAREN_READS_BACKGROUND is 'yes', but who_are_u.md is in '$session_dir/anti_karen/'." >&2
                exit 1
            end
        end
    end

    exit 0
else
    echo "Usage: boundaries/harvey_setup.fish [--pre|--post] [session_id]" >&2
    exit 2
end
