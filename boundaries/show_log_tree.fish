#!/usr/bin/env fish
set boundary_dir (status dirname)
"$boundary_dir/run_audit.fish" --finalize "$argv[1]"
or exit $status
set run_dir (jq -r .run_dir "$argv[1]")
echo
cat "$run_dir/log_tree.md"
