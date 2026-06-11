# 01 — The effort dial: what `--effort` actually buys on Fable 5

**Question:** Fable 5 removed the thinking off switch (`thinking: disabled` → HTTP 400). The effort dial (low/medium/high/xhigh/max) survives. Does it change speed? Does it change quality? And is `xhigh` — hidden in the app's effort picker for Fable — actually valid?

## Method

`claude -p "<prompt>" --model fable --effort <level>`, launch-week Claude Code CLI, cloud container, subscription surface. Write tools disallowed. Wall-clock includes CLI startup. Three task tiers, 5 rounds per level on the timed tiers (scripts: `effort_moderate.sh`, `speed_experiments.sh` sweep section, replication runner in `../02-speed-head-to-head/replication_rounds.sh`):

- **Easy:** explain in exactly 3 bullets why nested subagents cost more than a flat fan-out (no tools).
- **Hard:** count positive n < 1000 where n² ends in the same zero-padded 3 digits as n (checkable answer: 3 — the values 1, 376, 625). 1 round per level (`effort_hard.sh`).
- **Realistic:** read two repo files, reconcile an apparent contradiction in under 120 words (tools + judgment).

Baseline: the same realistic sweep on Opus 4.8, 5 rounds per level.

## Results

**Fable 5, seconds, mean of 5 rounds (sd):**

| Task | low | medium | high | xhigh | max |
|---|---|---|---|---|---|
| Easy | 11.4 (1.3) | 13.6 (0.6) | 14.6 (2.1) | 17.4 (1.1) | 36.5 (11.9) |
| Realistic | 21.2 (1.7) | 20.3 (2.8) | 23.9 (6.5) | 33.8 (7.3) | 42.2 (4.8) |

**Hard math, n=1 per level:** 12.3 / 11.7 / 16.9 / 18.2 / 34.2 — **correct answer with the same method at every level.**

**Opus 4.8 baseline, realistic task, mean of 5 rounds (sd):**

| | low | medium | high | xhigh | max |
|---|---|---|---|---|---|
| Opus 4.8 | 18.4 (5.4) | 19.6 (3.2) | 19.7 (1.7) | 25.3 (5.7) | 41.6 (14.5) |

**Control:** `--effort xyz` (made-up value) → explicit CLI warning ("Unknown --effort value 'xyz' — ignoring it... Valid values: low, medium, high, xhigh, max") and fallback to default. `--effort xhigh` on Fable passes silently and times between high and max.

## Findings

1. **The dial buys verification, not correctness.** Every run at every level returned the correct answer (math) or the identical verdict (realistic task). Higher effort added re-checks, caveats, and asides.
2. **Below max, the dial barely moves easy tasks** (11→17s); it bites from xhigh up on realistic ones (max ≈ 2x low).
3. **The dial's shape is not Fable-specific.** Opus 4.8 tracks Fable within noise at every level on the same task.
4. **`xhigh` is hidden in the app's picker for Fable but is a valid level** — confirmed against the xyz control.
5. **Max is expensive and noisy:** ~2–3x low with the largest spreads in the dataset (sd up to 14.5s).

Practical setting: run routine work at low; reserve xhigh/max for when you want the model to audit its own answer.

## Caveats

n=5 per timed cell (hard math n=1); wall-clock includes startup; one surface, launch week; effort semantics may be retuned post-launch.
