# boundaries/audit_logger.fish — Common logger function for all boundary scripts

function log_boundary
    set script $argv[1]
    set mode $argv[2]
    set session $argv[3]
    set code $argv[4]
    set details $argv[5]
    
    set status_str "PASS"
    if test "$code" -ne 0
        if test "$code" -eq 2
            set status_str "WARNING"
        else
            set status_str "FAIL"
        end
    end
    
    set timestamp (date -Iseconds)
    
    # Simple JSON escaping for details
    set escaped_details "null"
    if test -n "$details"
        if command -v jq >/dev/null 2>&1
            set escaped_details (echo "$details" | jq -R -s -c .)
        else
            set clean_details (string replace -a '"' '\\"' "$details")
            set escaped_details "\"$clean_details\""
        end
    end
    
    set log_file "/tmp/boundary_audit.jsonl"
    echo "{\"timestamp\": \"$timestamp\", \"script\": \"$script\", \"mode\": \"$mode\", \"session_id\": \"$session\", \"exit_code\": $code, \"status\": \"$status_str\", \"details\": $escaped_details}" >> "$log_file"
end

# Event handler that automatically logs when fish exits
function _on_boundary_exit --on-event fish_exit
    set -l exit_code $status
    
    if set -q BOUNDARY_NAME
        set -l details ""
        if set -q BOUNDARY_DETAILS
            set details "$BOUNDARY_DETAILS"
        end
        
        # We also pass global mode and session_id if they are defined
        set -l current_mode "unknown"
        if set -q mode
            set current_mode "$mode"
        end
        
        set -l current_session "unknown"
        if set -q session_id
            set current_session "$session_id"
        end
        
        log_boundary "$BOUNDARY_NAME" "$current_mode" "$current_session" "$exit_code" "$details"
    end
end
