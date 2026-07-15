#!/usr/bin/env fish

set -g BOUNDARY_DIR (status dirname)
set -g REPO_ROOT (path resolve "$BOUNDARY_DIR/..")
source "$BOUNDARY_DIR/audit_logger.fish"

function boundary_usage --argument-names script_name
    echo "Usage: boundaries/$script_name [--pre|--post] STATE_PATH" >&2
    return 2
end

function boundary_load_context --argument-names requested_state
    if test -z "$requested_state"; or not test -f "$requested_state"
        echo "Error [boundary]: State file does not exist: '$requested_state'." >&2
        return 2
    end
    set -g STATE_PATH (path resolve "$requested_state")
    set -g RUN_DIR (jq -er '.run_dir | strings' "$STATE_PATH" 2>/dev/null)
    or begin
        echo "Error [boundary]: Invalid run_dir in '$STATE_PATH'." >&2
        return 2
    end
    if test (path resolve "$RUN_DIR/state.json") != "$STATE_PATH"
        echo "Error [boundary]: state.json does not belong to its declared run_dir." >&2
        return 2
    end
    set -g SESSION_ID (jq -r '.current_session_id // empty' "$STATE_PATH")
end

function boundary_status_json
    set -l output (cd "$REPO_ROOT"; uv run python -m harvey_guy.pipeline status --state "$STATE_PATH" 2>&1)
    set -l exit_code $status
    echo (string join \n $output)
    return $exit_code
end

function boundary_expect_phase --argument-names script_name mode transition
    set -l expected $argv[4..-1]
    set -l output (boundary_status_json)
    set -l exit_code $status
    if test $exit_code -ne 0
        boundary_log "$script_name" "$mode" "$transition" $exit_code (string join \n $output)
        echo (string join \n $output) >&2
        return $exit_code
    end

    set -l phase (echo (string join \n $output) | jq -r .phase)
    set -g SESSION_ID (echo (string join \n $output) | jq -r '.current_session_id // empty')
    if not contains -- "$phase" $expected
        set -l detail "Expected phase "(string join ' or ' $expected)", found '$phase'."
        boundary_log "$script_name" "$mode" "$transition" 3 "$detail"
        echo "Error [$script_name]: $detail" >&2
        return 3
    end
    boundary_log "$script_name" "$mode" "$transition" 0 "Validated phase '$phase'."
    or return $status
    echo (string join \n $output)
end

function boundary_transition --argument-names script_name mode transition command_name
    set -l output (cd "$REPO_ROOT"; uv run python -m harvey_guy.pipeline "$command_name" --state "$STATE_PATH" 2>&1)
    set -l exit_code $status
    set -l text (string join \n $output)
    if test $exit_code -eq 0
        set -g SESSION_ID (echo "$text" | jq -r '.current_session_id // empty')
        set -l phase (echo "$text" | jq -r .phase)
        boundary_log "$script_name" "$mode" "$transition" 0 "Transition completed; phase='$phase'."
        or return $status
        echo "$text"
        return 0
    end
    boundary_log "$script_name" "$mode" "$transition" $exit_code "$text"
    echo "$text" >&2
    return $exit_code
end
