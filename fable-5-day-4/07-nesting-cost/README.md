# 07 — Nesting cost: depth vs a flat fan-out, strictly paired

**Question:** Same four leaf analyses + one synthesis — what does running them *nested* (manager spawns leaves) cost vs *flat* (harness spawns leaves directly)?

**Method:** `run_set06.sh` — 10 pairs, each pair run strictly serially with arm order alternating (flat-first on odd pairs, nested-first on even) to cancel order effects. Both arms do identical work: four haiku leaf analyses of four monthly CSVs plus one sonnet synthesis (`harness/flat.js`, `harness/nested.js`, shared `harness/lib.js`). Wall-clock and `total_cost_usd` from the CLI's JSON output, recorded in `set06.csv`.

**Results (7 complete pairs):**
- **Cost ratio nested/flat: med 2.54x** [1.25–3.42]. Flat med $0.41/run, nested med $1.14/run.
- Wall ratio: med 1.86x [0.70–3.47] — nested never came out cheaper (best pair still 1.25x), though it did once finish faster.
- This corrects the launch-week estimate of 1.6–1.8x ([fable-5-speed-depth/06](../../fable-5-speed-depth/06-nesting-cost/)), which came from fewer, unpaired runs.
- $13.25 metered across the set.

**Files:** `run_set06.sh`, `harness/`, `set06.csv`.

**Caveats:** 3 of 10 flat arms failed (one leaf exiting rc=1 through 3 retries; one run corrupted `~/.claude.json` mid-flight — the CLI auto-backed-up and recovered, worth knowing if you spawn many parallel `claude -p`). Failed pairs are in the CSV and excluded from ratios — ratios need both arms. The per-run output dirs are **not** published: the leaves analyze a private posts dataset, and their reports quote it. The harness prompts (in `harness/lib.js`) are verbatim, so you can rerun against any CSV with the same columns.
