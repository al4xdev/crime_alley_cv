#!/usr/bin/env fish
# boundaries/karen_gatekeeper.fish — Boundary validation hook for Gatekeeper

set mode $argv[1]
set session_id $argv[2]
set gatekeeper_exit $argv[3]

if test "$mode" = "--pre"
    # Pre-conditions:
    if test -z "$session_id"
        echo "Error [gatekeeper boundary]: session_id is missing." >&2
        exit 1
    end
    set session_dir "/tmp/karen_guard_$session_id"
    set eval_file "$session_dir/anti_karen/evaluation.md"
    if not test -f "$eval_file"
        echo "Error [gatekeeper boundary]: Evaluation report '$eval_file' is missing." >&2
        exit 1
    end
    exit 0

else if test "$mode" = "--post"
    # Post-conditions:
    if test -z "$gatekeeper_exit"
        echo "Error [gatekeeper boundary]: Missing exit code argument for --post." >&2
        exit 1
    end

    # Exit code validation
    if not string match -r '^[0123]$' "$gatekeeper_exit" >/dev/null
        echo "Error [gatekeeper boundary]: Gatekeeper exited with unexpected status code: $gatekeeper_exit" >&2
        exit 1
    end

    if test "$gatekeeper_exit" = "3"
        echo "Error [gatekeeper boundary]: Gatekeeper failed with a parsing or runtime error (status 3)." >&2
        exit 1
    end

    # If exit code was 0 (success) or 1 (max loops), verify that CV was copied back to the host .data/docs/cv.md
    if test "$gatekeeper_exit" = "0" -o "$gatekeeper_exit" = "1"
        set host_cv ".data/docs/cv.md"
        set session_dir "/tmp/karen_guard_$session_id"
        set session_cv "$session_dir/docs/cv.md"
        
        if not test -f "$host_cv"
            echo "Error [gatekeeper boundary]: CV was not copied back to host '$host_cv' on exit." >&2
            exit 1
        end

        # Ensure it matches the session CV
        set host_hash (sha256sum "$host_cv" | cut -d' ' -f1)
        set session_hash (sha256sum "$session_cv" | cut -d' ' -f1)
        if test "$host_hash" != "$session_hash"
            echo "Error [gatekeeper boundary]: Host CV does not match the final optimized session CV." >&2
            exit 1
        end
    end

    exit 0
else
    echo "Usage: boundaries/karen_gatekeeper.fish [--pre|--post] [session_id] [gatekeeper_exit_code]" >&2
    exit 2
end
