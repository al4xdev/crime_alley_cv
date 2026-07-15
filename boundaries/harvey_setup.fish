#!/usr/bin/env fish
source (status dirname)/common.fish
set mode $argv[1]
boundary_load_context "$argv[2]"; or exit $status
switch "$mode"
    case --pre
        boundary_expect_phase harvey_setup.fish "$mode" start_session ready
    case --post
        boundary_transition harvey_setup.fish "$mode" start_session start-session
    case '*'
        boundary_usage harvey_setup.fish
end
