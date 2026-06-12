# 04 — Audit economics: what does a real finding cost?

**Question:** Fable bills ~2x per token. What does it cost per *audit*, per *finding*, and per *the one bug that matters*?

**Method:** two complementary collections on the identical heavy-audit prompt from [02](../02-repo-questions-and-audits-n20/):
- `run_set07.py` — n=10 per model with `--output-format json`, so every run yields billed usage and the CLI's `total_cost_usd` directly (`set07.csv`).
- `mine_usage.py` / `mine_all_v4.py` — mine the same per-run billed usage for the set-02 audit runs out of the local Claude Code session traces (`audit_usage.csv`). Costs are priced at public API rates (Fable $10/$50, Opus $5/$25 per MTok; cache write ×1.25, read ×0.1) and validated to the cent against the CLI's own billing where both exist.
- `verify_costcard.py` / `verify_costcard2.py` — re-derive every published number from the CSVs + answer bodies: findings are counted as the longest consecutive numbered run in each report; "deep bug" hits are detected by string markers for a known cross-file numeric contradiction the audit can only catch by reading two files against each other.

**Results (pooled 30 audits per model across the June 11 + June 12 builds; per-audit $ from the 20-run v4 cells):**
- **Per audit:** Fable med $2.93 vs Opus $1.17 — **2.5x** (more than the 2x list-price ratio: Fable also writes more).
- **Per finding:** Fable med 14 findings vs Opus 7, so $0.21 vs $0.17 — **1.25x**.
- **Per deep bug:** Fable caught the cross-file contradiction **20/30**, Opus **2/30**. Expected spend per catch: **$4.40 vs $17.55** — a quarter of the cost, despite double the token price.
- Reversal check (it's not "Fable finds everything"): a same-file style clash was caught *more often by Opus* (16/30 vs 12/30). Depth and breadth are different axes.
- 1 of 40 v4 reports was unparseable for findings counting and is excluded from the findings medians (kept in the CSVs).

**Files:** `run_set07.py`, miners, verifiers, `set07.csv`, `set07_progress.log`, `audit_usage.csv`.

**Caveats:** matched configured effort (xhigh), both models. Two-build pooling applies only to the 30-run hit rates; $ medians come from single-build cells. ~$122 of API-priced spend metered across the audit collections. Raw report bodies are private (they quote the repo); the verifier scripts show exactly how they were counted.
