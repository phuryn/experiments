# 03 — Time-to-first-token + exact token counts at n=20

**Question:** Where does the "Fable is slow" feeling actually come from?

**Method:** `run_set03.py` — `--output-format stream-json` traces, strictly serial (first-token timing is the most startup-sensitive measurement, so no concurrent load), order shuffled per round with a fixed seed. Two prompts: an easy 3-bullet question and a math/reasoning problem with a checkable numeric answer. 20 rounds per cell (`--tag v4`), both models. CSV records first-any-event time, first-text time, total time, and exact input/output token counts per run.

**Results (v4, n=20):**
- **The starting pause is real and held:** first sign of life med 6.7s (Fable) vs 4.3s (Opus) — a 2.4s gap. At the median, +2.4 seconds of blank screen; Fable's worst start 16.7s, right tail kept.
- **The token claim flipped:** on launch day Fable wrote ~40% fewer output tokens on reasoning and finished sooner. At n=20 on the same math problem the token gap is **8%** (med 3,208 vs 3,412) and Fable's median finish is **1.5x behind** — though the tails crossed: the slowest single run in the cell is Opus's (101s vs Fable's 90s).
- Both models now write 2–3x more output tokens on this problem than their own launch-day logs. The build is tuned daily; day-one benchmarks age in days.
- All 40 graded math answers correct, both models.

**Files:** harness + analyzer, `set03.csv` (n=10), `set03-v4.csv` (n=20).

**Caveats:** flag-less runs at matched configured effort (xhigh), both models — see set README. The 360 runs behind the speed card metered 34.4M billed tokens (~$140 at public API rates).
