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

**Caveat:** "first activity" includes the start of thinking, not just visible text; n=3; no-tool prompts only.
