# 03 — Time-to-first-token & output tokens, Opus 4.8 vs Fable 5

**Question:** the launch discourse calls Fable slow. Where does the slowness actually live: before the first token, or in generation?

**Method:** `ttft.py` runs `claude -p` with `--output-format stream-json --include-partial-messages`, timestamps the first model activity event, and reads exact `output_tokens` / `input_tokens` from the API's result event. Two no-tool prompts (an easy explanation, a checkable math problem), both models, 3 rounds each. Raw CSV in `ttft.log` (columns: tag, round, prompt, model, rc, t_first_activity, t_total, output_tokens, input_tokens, chars).

## Results (n=3 per cell)

**First model activity (seconds):**

| Prompt | Opus 4.8 | Fable 5 |
|---|---|---|
| easy | 4.7 / 5.1 / 5.3 | 8.0 / 8.2 / 7.4 |
| reasoning | 11.6 / 7.0 / 6.7 | 8.2 / 6.9 / 7.9 |

On the easy prompt the gap is consistent and non-overlapping: Fable's first activity comes ~3 seconds later.

**Output tokens and total time (reasoning prompt, all 6 runs correct):**

| Round | Opus tokens | Fable tokens | Opus total | Fable total |
|---|---|---|---|---|
| 1 | 1,079 | 567 | 24.8s | 15.3s |
| 2 | 1,288 | 823 | 20.7s | 15.6s |
| 3 | 1,487 | 786 | 22.1s | 16.1s |

## Findings

1. **Fable starts ~3s later** on identical prompts. This pre-work pause is the likely source of the "it crawls" perception.
2. **Fable is terser, not slower, in flight:** ~40% fewer output tokens on the reasoning task and 5–9s faster end to end, with both models correct every round.
3. Prompt caching is visible in the data: `input_tokens` drops from 2,222 (first run) to 2 (subsequent runs).

> **Update (June 11–12, 2026 — retested at n=20):** Finding 2 flipped. The launch-day "~40% fewer tokens, finishes sooner" was 39% fewer (median 786 vs 1,288) off n=3 cells. At n=10 the reasoning-prompt gap shrank to **12.9% fewer** (median 2,112 vs 2,426), and Fable finished **1.49x behind**, not ahead — median 43.3s vs 29.0s, reversing the launch-day 5–9s lead. At n=20 the gap was **8%**, still ~1.5x behind. What moved most: **both models now write 2–3x more output tokens than these very logs, ~48h later** — the build was being tuned daily, so the token counts rot faster than the ratios. Finding 1 held: the starting pause is still there (med 6.7s vs 4.3s at n=20). Full retest: [../../fable-5-day-4/03-ttft-tokens-n20/](../../fable-5-day-4/03-ttft-tokens-n20/).

**Caveat:** "first activity" includes the start of thinking, not just visible text; n=3; no-tool prompts only.
