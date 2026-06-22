#!/usr/bin/env fish
# boundaries/bill_harvey.fish — Boundary validation hook for carry-forward of optimized CV

set mode $argv[1]
set session_id $argv[2]

if test "$mode" = "--pre"
    # Pre-conditions:
    if test -z "$session_id"
        echo "Error [carry-forward boundary]: session_id is missing." >&2
        exit 1
    end
    set session_dir "/tmp/karen_guard_$session_id"
    set session_cv "$session_dir/docs/cv.md"
    if not test -f "$session_cv"
        echo "Error [carry-forward boundary]: Session CV '$session_cv' is missing." >&2
        exit 1
    end

    set host_cv ".data/docs/cv.md"
    if test -f "$host_cv"
        set session_hash (sha256sum "$session_cv" | cut -d' ' -f1)
        set host_hash (sha256sum "$host_cv" | cut -d' ' -f1)
        if test "$session_hash" = "$host_hash"
            echo "Warning [carry-forward boundary]: Session CV is identical to Host CV. Nothing to carry forward?"
        end
    end
    exit 0

else if test "$mode" = "--post"
    # Post-conditions:
    set session_dir "/tmp/karen_guard_$session_id"
    set session_cv "$session_dir/docs/cv.md"
    set host_cv ".data/docs/cv.md"
    
    # 1. Perform CV copy (carry-forward)
    mkdir -p (dirname "$host_cv")
    cp -f "$session_cv" "$host_cv"
    if not test -f "$host_cv"
        echo "Error [carry-forward boundary]: Failed to copy session CV to '$host_cv'." >&2
        exit 1
    end

    # 2. Increment CURRENT_LOOP and write state JSON
    set checkpoint_file "/tmp/karen_guard_loop_state.json"
    if test -f "$checkpoint_file"
        set state_json (cat "$checkpoint_file")
        # Extract variables
        set current_loop (echo $state_json | jq -r '.current_loop')
        set fit_score (echo $state_json | jq -r '.fit_score')
        
        if not string match -r '^\d+$' "$current_loop" >/dev/null
            set current_loop 0
        end
        # Increment
        set current_loop (math "$current_loop + 1")
        
        # Write back new state JSON
        echo "{\"current_loop\": $current_loop, \"fit_score\": $fit_score, \"session_id\": \"$session_id\"}" > "$checkpoint_file"
        
        # Verify checkpoint update
        set new_loop (cat "$checkpoint_file" | jq -r '.current_loop')
        if test "$new_loop" -ne "$current_loop"
            echo "Error [carry-forward boundary]: Failed to update loop checkpoint count." >&2
            exit 1
        end
    else
        echo "Warning [carry-forward boundary]: Checkpoint file '$checkpoint_file' not found. Creating it."
        echo "{\"current_loop\": 1, \"fit_score\": null, \"session_id\": \"$session_id\"}" > "$checkpoint_file"
    end

    exit 0
else
    echo "Usage: boundaries/bill_harvey.fish [--pre|--post] [session_id]" >&2
    exit 2
end
