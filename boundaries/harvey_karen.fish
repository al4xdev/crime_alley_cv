#!/usr/bin/env fish
source (status dirname)/common.fish
set mode $argv[1]
boundary_load_context "$argv[2]"; or exit $status
switch "$mode"
    case --pre
        boundary_expect_phase harvey_karen.fish "$mode" record_evaluation karen_ready
    case --post
        boundary_transition harvey_karen.fish "$mode" record_evaluation record-evaluation
    case '*'
        boundary_usage harvey_karen.fish
end
