#!/usr/bin/env fish
# boundaries/show_log_tree.fish — Visual helper to display the boundary audit log tree

set log_file "/tmp/boundary_audit.jsonl"

if not test -f "$log_file"
    echo "No boundary log file found at $log_file. Run the pipeline first."
    exit 0
end

echo "🔒 Boundary Audit Log Tree:"
echo "=========================="

while read -la line
    if test -z "$line"
        continue
    end
    
    # Extract fields using jq if available, otherwise fallback to simple extraction
    if command -v jq >/dev/null 2>&1
        set ts (echo "$line" | jq -r '.timestamp')
        # Parse timezone out of timestamp for clean reading (e.g. 2026-07-10T20:17:26-03:00 -> 20:17:26)
        set time_str (string sub -s 12 -l 8 "$ts")
        set script (echo "$line" | jq -r '.script')
        set mode (echo "$line" | jq -r '.mode')
        set session (echo "$line" | jq -r '.session_id')
        set status_str (echo "$line" | jq -r '.status')
        set details (echo "$line" | jq -r '.details')
        
        # Color coding
        set color_indicator "🟢"
        if test "$status_str" = "FAIL"
            set color_indicator "🔴"
        else if test "$status_str" = "WARNING"
            set color_indicator "🟡"
        end
        
        set short_session (string sub -l 8 "$session")
        
        if test "$details" != "null" -a -n "$details"
            echo "[$time_str] $color_indicator $script ($mode) [session: $short_session] - $status_str ($details)"
        else
            echo "[$time_str] $color_indicator $script ($mode) [session: $short_session] - $status_str"
        end
    else
        # Fallback raw line
        echo "$line"
    end
end < "$log_file"
