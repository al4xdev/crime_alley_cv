#!/usr/bin/env fish
source (status dirname)/common.fish
set mode $argv[1]
boundary_load_context "$argv[2]"; or exit $status
set audit_log "$RUN_DIR/logs/boundary_audit.jsonl"

switch "$mode"
    case --init
        mkdir -p "$RUN_DIR/logs" "$RUN_DIR/sessions"
        touch "$audit_log"
        boundary_log run_audit.fish "$mode" initialize_audit 0 "Run-scoped audit journal ready."
        or exit $status
        echo "$audit_log"
    case --finalize
        if not test -f "$audit_log"
            echo "Error [run audit]: Missing audit log '$audit_log'." >&2
            exit 1
        end
        boundary_log run_audit.fish "$mode" finalize_run 0 "Final log consolidation started."
        or exit $status
        set output (cd "$REPO_ROOT"; uv run python -m harvey_guy.finalize_run --state "$STATE_PATH" 2>&1)
        set exit_code $status
        set text (string join \n $output)
        boundary_log run_audit.fish "$mode" finalize_run $exit_code "$text"
        set audit_exit_code $status
        if test $audit_exit_code -ne 0
            exit $audit_exit_code
        end
        if test $exit_code -eq 0
            # Regenerate once so the completion event itself appears in the final tree.
            cd "$REPO_ROOT"; and uv run python -m harvey_guy.finalize_run --state "$STATE_PATH"
            exit $status
        end
        echo "$text" >&2
        exit $exit_code
    case '*'
        echo "Usage: boundaries/run_audit.fish [--init|--finalize] STATE_PATH" >&2
        exit 2
end
