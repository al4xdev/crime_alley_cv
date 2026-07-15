#!/usr/bin/env fish
source (status dirname)/common.fish
set mode $argv[1]
boundary_load_context "$argv[2]"; or exit $status
switch "$mode"
    case --pre
        boundary_expect_phase bill_harvey.fish "$mode" commit_bill bill_running
    case --post
        boundary_transition bill_harvey.fish "$mode" commit_bill commit-bill
    case '*'
        boundary_usage bill_harvey.fish
end
