# 02 — Speed head-to-head: Opus 4.8 vs Fable 5

**Question:** the day-one discourse says Fable is slow ("even on simple tasks it would crawl"). Is it, measured?

## Method

Five short repo questions (1–2 file reads each, one-sentence answers), both models at default effort, **5 rounds = 50 timed answers**. `claude -p`, launch-week CLI, cloud container, subscription surface, write tools disallowed. Wall-clock includes CLI startup. Script: `replication_rounds.sh` (speed section); round 1 in `speed_experiments.log`; rounds 2–5 in `replication_rounds.log` (CSV: `RES,round,exp,model,question,rc,seconds,chars`).

Plus one heavier task, 1 round per model: a multi-file judgment audit (find contradictions across three style-system files, quote both sides, recommend fixes).

## Results

**Totals per round (5 questions each):**

| Round | Opus 4.8 | Fable 5 | Ratio |
|---|---|---|---|
| 1 | 38.2s | 63.4s | 1.66 |
| 2 | 60.1s | 70.1s | 1.17 |
| 3 | 41.7s | 53.1s | 1.27 |
| 4 | 34.7s | 52.0s | 1.50 |
| 5 | 37.3s | 57.1s | 1.53 |
| **Mean ratio** | | | **1.42 (sd 0.20)** |

Per-answer means: Opus 8.5s (sd 5.7), Fable 11.8s (sd 3.8). Every one of the 50 answers was correct, both models. Output length on these short answers was effectively equal (mean 97 vs 104 chars).

**The slowest single answer in the whole dataset was Opus's** (34.5s, round 2), not Fable's (worst: 22.6s).

**Heavier multi-file audit (n=1 per model):** Opus 59.2s / 3,094 chars; Fable 62.8s / 4,149 chars — the time gap vanishes, and Fable returns ~34% more findings text.

## Findings

1. **The trivial-task tax is real but modest: ~1.4x** (round ratios 1.2–1.7), seconds not minutes in absolute terms.
2. **The tax disappears on heavier work** — parity on the multi-file audit, with more output. Consistent with experiment 01: Opus and Fable track each other within noise on realistic tasks at every effort level.
3. **"It crawls on simple tasks" did not reproduce.** See experiment 03 for where the slow *feeling* comes from (a ~3s starting pause).
4. Fable also had *lower* variance per answer than Opus (sd 3.8 vs 5.7) — steadier, not just slower.

> **Update (June 11–12, 2026 — retested at n=20):** Finding 2 did not survive. The "parity on heavier work" read rested on a single audit pair (the 1.06x above); one lucky pair. Repeated as 10 strictly-paired heavy 3-file audits, the tax was a **1.32x median at n=10** [0.99–1.88] (one pair of ten hit parity at 0.99x), and **1.29x median at n=20** [0.92–1.70]. So the tax flattens as the task grows heavier, it does not vanish. The rest held: trivial-task ratio 1.48x, and every graded answer still correct. Full retest: [../../fable-5-day-4/02-repo-questions-and-audits-n20/](../../fable-5-day-4/02-repo-questions-and-audits-n20/).

## Caveats

One surface, one container, launch week; wall-clock includes startup; heavier-task comparison is n=1 per model; both models may be retuned at any time.
