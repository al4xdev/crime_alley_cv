#!/usr/bin/env fish
source (status dirname)/common.fish
set mode $argv[1]
boundary_load_context "$argv[2]"; or exit $status
switch "$mode"
    case --pre
        boundary_transition gatekeeper_donna.fish "$mode" prepare_donna prepare-donna
    case --post
        boundary_transition gatekeeper_donna.fish "$mode" complete_donna complete-donna
    case '*'
        boundary_usage gatekeeper_donna.fish
end
