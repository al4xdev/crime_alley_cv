#!/usr/bin/env fish

# Find container ID running crime_alley_pipeline
set container_id (docker ps --filter "ancestor=crime_alley_pipeline" --format "{{.ID}}" | head -n 1)

if test -n "$container_id"
    echo "=================================================="
    echo "Active Container ID: $container_id"
    
    # Check loop state checkpoint
    set state_json (docker exec $container_id cat /tmp/karen_guard_loop_state.json 2>/dev/null)
    if test -n "$state_json"
        echo "Current Loop State Checkpoint:"
        echo $state_json | jq .
        
        set session_id (echo $state_json | jq -r '.session_id')
        if test -n "$session_id" -a "$session_id" != "null" -a "$session_id" != "previous_or_null"
            echo "Session ID: $session_id"
            echo "--------------------------------------------------"
            echo "Session directories inside container /tmp:"
            docker exec $container_id tree -L 3 -a /tmp 2>/dev/null || echo "tree command not found inside container"
            
            echo "--------------------------------------------------"
            echo "Tail of Karen run log (stdout):"
            docker exec $container_id tail -n 10 /tmp/karen_guard_$session_id/anti_karen/karen_run.log 2>/dev/null || echo "No logs yet"
            
            echo "--------------------------------------------------"
            echo "Tail of Karen run error (stderr):"
            docker exec $container_id tail -n 10 /tmp/karen_guard_$session_id/anti_karen/karen_run.err 2>/dev/null || echo "No stderr yet"
            
            echo "--------------------------------------------------"
            echo "Tail of Harvey core log:"
            docker exec $container_id tail -n 10 /tmp/karen_guard_$session_id/anti_karen/karen_guard_core.log 2>/dev/null || echo "No core logs yet"
        end
    else
        echo "No /tmp/karen_guard_loop_state.json file found inside the container yet."
    end
    echo "=================================================="
else
    echo "No active container running crime_alley_pipeline."
    # Let's check host runs directory for the latest status
    set latest_run (find .runs -maxdepth 1 -mindepth 1 -not -name ".*" 2>/dev/null | head -n 1)
    if test -n "$latest_run"
        echo "Latest run on host: $latest_run"
        if test -f "$latest_run/scores.csv"
            echo "Scores history:"
            cat "$latest_run/scores.csv"
        end
    else
        echo "No run history found in .runs/ on host."
    end
end

