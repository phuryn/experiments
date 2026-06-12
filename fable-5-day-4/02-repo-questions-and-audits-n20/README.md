# 02 — Repo questions + heavy audits at n=20

**Question:** What does Fable 5 cost in wall-clock time, on trivial lookups vs real multi-file work?

**Method:** `run_set02.py` — per round and model: five short repo-lookup questions (Q1–Q5, one-sentence answers against a private content repo), one heavy audit (find and reconcile contradictions across three style-guide files, "be thorough"), and a pin-check (Q1 at explicit `--effort high`). 20 rounds (`--tag v4`), 3 matched lanes, fixed-seed shuffle, write tools disallowed. The n=10 June-11 collection (`set02.csv`) kept separate.

**Results (v4, n=20):**
- Trivial questions (200 graded answers): Fable med **1.48x** Opus wall-clock. All answers correct, both models.
- Heavy audits (20 pairs): Fable med **1.29x** [best 0.92x, worst 1.70x] — two of twenty pairs beat Opus outright. The launch-week "parity on real work" claim flipped; the tax flattens with task size but doesn't vanish.
- The audits also produced the findings data: Fable reports surfaced a median **14 distinct findings vs Opus 7** on the identical prompt — the receipts for that counting live in [04-audit-economics](../04-audit-economics/).

**Files:** harness + retry + analyzer, `set02.csv`, `set02-v4.csv`, progress logs.

**Caveats:** flag-less rows ran at the machine's configured effort (xhigh) on both models — matched, so ratios stand; see the set README. Answer bodies are private (they quote the repo); the CSVs are content-free.
