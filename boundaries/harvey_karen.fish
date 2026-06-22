#!/usr/bin/env fish
# boundaries/harvey_karen.fish — Boundary validation hook for Karen Guard

set mode $argv[1]
set session_id $argv[2]

if test "$mode" = "--pre"
    # Pre-conditions:
    if test -z "$session_id"
        echo "Error [Karen boundary]: session_id is missing." >&2
        exit 1
    end
    set session_dir "/tmp/karen_guard_$session_id"
    if not test -d "$session_dir"
        echo "Error [Karen boundary]: Session directory '$session_dir' does not exist." >&2
        exit 1
    end

    # 1. Verify docs in session
    for doc in cv.md job.md
        if not test -f "$session_dir/docs/$doc"
            echo "Error [Karen boundary]: Missing input file '$session_dir/docs/$doc'." >&2
            exit 1
        end
    end

    # 2. Verificação de Liveness Autenticada da API Gemini (agy models)
    if not agy models >/dev/null 2>&1
        echo "Error [Karen boundary]: Antigravity CLI ('agy') authentication is invalid or expired. Please run 'agy' on the host first to authenticate." >&2
        exit 1
    end

    exit 0

else if test "$mode" = "--post"
    # Post-conditions:
    set session_dir "/tmp/karen_guard_$session_id"
    
    # Verify evaluation report was generated
    set eval_file "$session_dir/anti_karen/evaluation.md"
    if not test -f "$eval_file"
        echo "Error [Karen boundary]: Karen's audit report '$eval_file' was not generated." >&2
        exit 1
    end

    set size (stat -c %s "$eval_file" 2>/dev/null; or stat -f %z "$eval_file" 2>/dev/null; or echo 0)
    if test "$size" -lt 100
        echo "Error [Karen boundary]: Karen's audit report is empty or too small ($size bytes)." >&2
        exit 1
    end

    # Verify that score is present in some form in the file
    if not grep -q -i "score" "$eval_file"
        echo "Error [Karen boundary]: Karen's report does not seem to contain a Technical Fit Score." >&2
        exit 1
    end

    exit 0
else
    echo "Usage: boundaries/harvey_karen.fish [--pre|--post] [session_id]" >&2
    exit 2
end
