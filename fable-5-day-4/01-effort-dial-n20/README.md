# 01 — Effort dial at n=20

**Question:** Does `--effort` change speed or quality, and where do Fable 5 and Opus 4.8 actually separate?

**Method:** `run_set01.py` — three task tiers (easy: 3-bullet explanation; realistic: two-file contradiction check against a private repo; hard: a number-theory puzzle), every `--effort` level `low|medium|high|xhigh|max`, both models, 20 rounds per cell (`--tag v4`), 3 matched lanes, fixed-seed shuffle. Plus a control lane: `--effort xyz` (a made-up level), n=20. `retry_set01.py` re-runs only combos lacking a clean rc=0 row (session-limit hits); `analyze_set01.py` / `stats_v4.py` produce the medians. The n=10 June-11 collection (`set01.csv`) is kept separately and never pooled with `set01-v4.csv`.

**Results (v4, n=20 per cell):**
- Easy-task medians (Fable): low 12.0 / medium 13.1 / high 13.6 / xhigh 18.5 / max 36.5s — the dial barely bites until the top.
- Realistic-task medians (Fable vs Opus): low 18.7/19.1 · medium 32.3/21.8 · high 27.4/23.5 · xhigh 35.9/30.4 · **max 60.8/49.0**. Max is the only level where the models clearly separate, and that gap moved between builds (the June-11 build showed a dead heat).
- Every graded hard-puzzle answer correct at every level — the extra seconds bought re-verification, not better answers.
- **The `xyz` control:** n=20, med 17.6s ≈ the explicit-xhigh distribution (18.5s), nowhere near explicit-high (13.6s). The CLI silently falls back to your *configured* settings level on an unrecognized `--effort` value — not to the model default.

**Files:** harness + retry + analyzers, `set01.csv` (n=10), `set01-v4.csv` (n=20), progress logs.

**Caveats:** see the set README for the matched-xhigh disclosure on flag-less rows (only the `pin`/default cells are affected; the dial sweep above used explicit flags). The 420 runs behind the effort-dial card metered 44.5M billed tokens (~$149 at public API rates).
