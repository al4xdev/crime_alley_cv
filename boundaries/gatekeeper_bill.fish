#!/usr/bin/env fish
# boundaries/gatekeeper_bill.fish — Boundary validation hook for Bill CV revision

set mode $argv[1]
set session_id $argv[2]

if test "$mode" = "--pre"
    # Pre-conditions:
    if test -z "$session_id"
        echo "Error [Bill boundary]: session_id is missing." >&2
        exit 1
    end
    set session_dir "/tmp/karen_guard_$session_id"
    if not test -d "$session_dir"
        echo "Error [Bill boundary]: Session directory '$session_dir' does not exist." >&2
        exit 1
    end

    # Ensure anti_karen exists
    mkdir -p "$session_dir/anti_karen"

    # 1. Save hash of initial cv.md
    set cv_file "$session_dir/docs/cv.md"
    if not test -f "$cv_file"
        echo "Error [Bill boundary]: Missing CV file '$cv_file'." >&2
        exit 1
    end
    sha256sum "$cv_file" | cut -d' ' -f1 > "$session_dir/anti_karen/pre_bill_cv_hash.txt"

    # 2. Save hashes of input sources to prevent context fraud/modification
    set hash_file "$session_dir/anti_karen/pre_bill_hashes.txt"
    echo -n "" > "$hash_file"
    
    # We track job.md, company_info.md, docs/who_are_u.md, anti_karen/who_are_u.md
    for doc in docs/job.md company_info.md docs/who_are_u.md anti_karen/who_are_u.md
        set path "$session_dir/$doc"
        if test -f "$path"
            set file_hash (sha256sum "$path" | cut -d' ' -f1)
            echo "$doc:$file_hash" >> "$hash_file"
        end
    end

    # 3. Create a snapshot of currently modified files in host repository
    git diff --name-only > "$session_dir/anti_karen/pre_bill_git_diff.txt"

    exit 0

else if test "$mode" = "--post"
    # Post-conditions:
    set session_dir "/tmp/karen_guard_$session_id"
    
    # 1. Verify cv.md was actually modified
    set cv_file "$session_dir/docs/cv.md"
    if not test -f "$cv_file"
        echo "Error [Bill boundary]: CV file '$cv_file' was deleted during editing." >&2
        exit 1
    end
    
    set initial_hash_path "$session_dir/anti_karen/pre_bill_cv_hash.txt"
    if not test -f "$initial_hash_path"
        echo "Error [Bill boundary]: Missing initial CV hash snapshot." >&2
        exit 1
    end
    
    set initial_hash (cat "$initial_hash_path")
    set current_hash (sha256sum "$cv_file" | cut -d' ' -f1)
    if test "$initial_hash" = "$current_hash"
        echo "Error [Bill boundary]: CV file '$cv_file' was not modified by Bill." >&2
        exit 1
    end

    # 2. Check for context fraud (integrity of job.md, company_info.md, who_are_u.md)
    set hash_file "$session_dir/anti_karen/pre_bill_hashes.txt"
    if not test -f "$hash_file"
        echo "Error [Bill boundary]: Missing integrity hashes snapshot." >&2
        exit 1
    end
    
    while read -la line
        if test -z "$line"
            continue
        end
        # Format is doc:hash
        set parts (string split -m 1 ":" "$line")
        set doc $parts[1]
        set expected_hash $parts[2]
        
        set path "$session_dir/$doc"
        if not test -f "$path"
            echo "Error [Bill boundary]: Ground-truth file '$path' was deleted or moved during editing." >&2
            exit 3 # Exit code 3 for integrity failure
        end
        
        set actual_hash (sha256sum "$path" | cut -d' ' -f1)
        if test "$expected_hash" != "$actual_hash"
            echo "Error [Bill boundary]: Integrity violation! File '$path' was modified by Bill (context fraud prevention)." >&2
            exit 3 # Exit code 3 for integrity failure
        end
    end < "$hash_file"

    # 3. Verify no host repository files were modified by Bill
    set initial_diff_path "$session_dir/anti_karen/pre_bill_git_diff.txt"
    if not test -f "$initial_diff_path"
        echo "Error [Bill boundary]: Missing initial host git diff snapshot." >&2
        exit 1
    end

    set current_diff (git diff --name-only)
    set initial_diff (cat "$initial_diff_path")
    
    # We want to check if any file in current_diff was not in initial_diff
    # We can do this with string match or nested loops
    for file in $current_diff
        if not string match -q "$file" $initial_diff
            echo "Error [Bill boundary]: Unauthorized file modification! Bill modified host repository file: '$file'." >&2
            exit 1
        end
    end

    exit 0
else
    echo "Usage: boundaries/gatekeeper_bill.fish [--pre|--post] [session_id]" >&2
    exit 2
end
