#!/usr/bin/env fish
source (status dirname)/common.fish
set mode $argv[1]
boundary_load_context "$argv[2]"; or exit $status
switch "$mode"
    case --pre
        boundary_expect_phase harvey_shadow.fish "$mode" mark_shadow_ready shadow_running
    case --post
        boundary_transition harvey_shadow.fish "$mode" mark_shadow_ready shadow-ready
    case '*'
        boundary_usage harvey_shadow.fish
end
