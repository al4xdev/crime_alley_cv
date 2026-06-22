#!/usr/bin/env fish
# boundaries/harvey_depchecker.fish — Boundary validation hook for Dependency Checker

set mode $argv[1]
set session_id $argv[2]

if test "$mode" = "--pre"
    # Pre-conditions: Nenhuma especial para depchecker
    exit 0
else if test "$mode" = "--post"
    # Post-conditions:
    set marker_file ".data/docs/.dependencies_checked.md"
    if not test -f "$marker_file"
        echo "Error [depchecker boundary]: Marker file '$marker_file' does not exist." >&2
        exit 1
    end

    # Check that crucial tools passed
    for tool in Python uv Docker at Git wl-copy
        if not grep -q -i "$tool" "$marker_file"
            echo "Error [depchecker boundary]: Tool '$tool' not mentioned in verification report." >&2
            exit 1
        end
    end

    if grep -q "FAIL" "$marker_file"
        echo "Error [depchecker boundary]: Dependency report contains FAIL status." >&2
        exit 1
    end

    exit 0
else
    echo "Usage: boundaries/harvey_depchecker.fish [--pre|--post] [session_id]" >&2
    exit 2
end
