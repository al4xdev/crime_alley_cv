#!/usr/bin/env fish

function boundary_log --argument-names script_name mode transition exit_code details
    if not set -q RUN_DIR REPO_ROOT
        echo "Error [boundary audit]: Boundary context is not loaded." >&2
        return 2
    end

    set -l session_argument
    if set -q SESSION_ID; and test -n "$SESSION_ID"
        set session_argument --session-id "$SESSION_ID"
    end
    cd "$REPO_ROOT"; and uv run python -m harvey_guy.audit \
        --run-dir "$RUN_DIR" \
        --script "$script_name" \
        "--mode=$mode" \
        --transition "$transition" \
        $session_argument \
        --exit-code "$exit_code" \
        "--details=$details"
end
