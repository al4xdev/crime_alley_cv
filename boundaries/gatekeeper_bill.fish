#!/usr/bin/env fish
source (status dirname)/common.fish
set mode $argv[1]
boundary_load_context "$argv[2]"; or exit $status
switch "$mode"
    case --pre
        boundary_transition gatekeeper_bill.fish "$mode" prepare_bill prepare-bill
    case --post
        boundary_expect_phase gatekeeper_bill.fish "$mode" prepare_bill bill_running
    case '*'
        boundary_usage gatekeeper_bill.fish
end
