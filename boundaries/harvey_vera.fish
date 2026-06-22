#!/usr/bin/env fish
# boundaries/harvey_vera.fish — Boundary validation hook for Vera Onboarding

set mode $argv[1]
set session_id $argv[2]

if test "$mode" = "--pre"
    # Pre-conditions: Nenhuma especial
    exit 0
else if test "$mode" = "--post"
    # Post-conditions:
    set background_file ".data/docs/who_are_u.md"
    if not test -f "$background_file"
        echo "Error [Vera boundary]: Background file '$background_file' does not exist." >&2
        exit 1
    end

    # Check size > 100 bytes
    set size (stat -c %s "$background_file" 2>/dev/null; or stat -f %z "$background_file" 2>/dev/null; or echo 0)
    if test "$size" -lt 100
        echo "Error [Vera boundary]: Background file is too small ($size bytes)." >&2
        exit 1
    end

    # Check that it contains markdown headings
    if not grep -q "^#" "$background_file"
        echo "Error [Vera boundary]: Background file does not seem to contain Markdown formatting." >&2
        exit 1
    end

    exit 0
else
    echo "Usage: boundaries/harvey_vera.fish [--pre|--post] [session_id]" >&2
    exit 2
end
