#!/usr/bin/env fish
source (status dirname)/common.fish
set mode $argv[1]
boundary_load_context "$argv[2]"; or exit $status
switch "$mode"
    case --pre
        boundary_expect_phase karen_gatekeeper.fish "$mode" evaluation_gate karen_ready
    case --post
        boundary_expect_phase karen_gatekeeper.fish "$mode" evaluation_gate needs_revision coaching_ready
    case '*'
        boundary_usage karen_gatekeeper.fish
end
