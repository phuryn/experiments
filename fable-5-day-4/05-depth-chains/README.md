# 05 — CLI depth chains: where's the wall?

**Question:** The Task tool caps subagent depth at 5. Does any platform wall exist when agents compose through the CLI instead?

**Method:** `level.sh` — each level is a `claude -p` (haiku) whose only job is to run `bash level.sh N+1` via its Bash tool and report its child's first line. `run_set04.sh` launches ten 6-level chains (3 concurrent, each in its own dir). `run_set08.py` (the `cli` arm) pushes ten fresh chains to **depth 10** with a cheap prompt, then verifies each chain's own artifacts: `timeline.log` (epoch-stamped start/done per level) and the `FLOOR` line in `root_output.txt`.

**Results:**
- Depth 6: **10/10 complete**, 49–57s round trip per chain.
- Depth 10: **10/10 complete**, 84–93s. Every `timeline.log` shows all ten levels starting ~6s apart and unwinding cleanly; every root output ends `L1 OK, child said: L2 OK, ... FLOOR 10`.
- **No platform resistance at any depth tested.** No refusal, no throttle, no error mentioning depth. The depth-5 cap is a Task-tool property, not a platform one. Outside the Task tool, the only ceiling we found is the invoice.

**Files:** `level.sh`, `run_set04.sh`, `run_set08.py` (shared with [06](../06-recursive-workflows/)), `set08.csv`, per-chain artifacts in `results-depth6/` (c00 = smoke at depth 3) and `results-depth10/`.

**Gotchas (kept in the receipts):** the early `cli` FAIL rows in `set08.csv` (rc=1 in 0–6s) are a Windows harness bug, not a model failure — a bare `"bash"` from Python's `subprocess` resolves to *WSL* bash, which can't read `C:/` paths; the fix is the explicit Git-Bash path you'll find in `run_set08.py`. Rows kept because trimming embarrassing rows is how datasets start lying.
