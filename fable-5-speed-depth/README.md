# Fable 5: Speed & Depth — Launch-Week Experiments (June 9–10, 2026)

> **⚠ Retested at n=20 on June 11–12 — several headline claims below did not survive.** The retest lives in [fable-5-day-4/](../fable-5-day-4/). What flipped: "parity on real multi-step work" → a 1.29x median time tax on heavy audits; "~40% fewer output tokens, finishes sooner" → 8% fewer and 1.5x behind; nesting cost "1.6–1.8x" → 2.54x median over paired runs. What held: the ~1.6x trivial-task ratio (1.48x), the starting pause (med 6.7s vs 4.3s), correctness across the effort dial, and "no depth wall" — extended to depth 10. This folder is kept as-is, as the record of what launch-week numbers looked like and how fast they aged.

The speed-and-depth set of receipts behind [Claude Fable 5 for PMs: The Ultimate Guide](https://www.productcompass.pm/p/claude-fable-5-guide) (Product Compass). Six experiments on how fast Fable 5 runs and how deep its agents nest. Every number in the guide that isn't sourced to Anthropic comes from a script and a log in this folder.

All runs: launch-week Claude Code CLI (`claude -p`, non-interactive), cloud container, subscription surface. Wall-clock times include CLI startup, so ratios are more trustworthy than absolutes.

| # | Experiment | Question | Headline result |
|---|---|---|---|
| [01](01-effort-dial/) | Effort dial | Does `--effort` change speed or quality? | The dial only bites on tasks that need it; correctness unchanged at every level; `xhigh` is hidden in the app picker for Fable but valid in the CLI |
| [02](02-speed-head-to-head/) | Speed head-to-head | Is Fable slower than Opus 4.8? | ~1.6x on trivial one-shot questions; parity on real multi-step work |
| [03](03-ttft-tokens/) | Time-to-first-token & output tokens | Where does the "slow" feeling come from? | Fable starts ~3s later than Opus; in flight it uses ~40% fewer output tokens on reasoning and finishes sooner |
| [04](04-depth-chain/) | Depth chain | How deep can CLI-composed agents nest? | 6 levels, no platform wall (the depth=5 cap applies to Task-tool subagents only) |
| [05](05-recursive-workflows/) | Recursive workflows | Can each level write the next level's orchestrator? | Yes: 4 generated orchestrators, all correct on first write, L2→L6 in 107s |
| [06](06-nesting-cost/) | Nesting cost | What does depth cost vs a flat fan-out? | 1.6–1.8x; manager overhead falls from 71% to 32% of budget as leaves do real work |

## Method notes & caveats

- Sample sizes are listed per experiment; early cells were n=1 and the timing experiments were re-run for 5 rounds after one ~6s network-variance outlier showed up.
- Subscription surface only (per-token API access opens June 22); API latencies may differ.
- Launch-week build. Anthropic is actively tuning classifiers and system prompts, so expect drift.
- Tasks reference files in a private content repo; the prompts are quoted verbatim in the scripts, so you can rebuild equivalents against any repo.

## License

MIT. Use anything here however you like; a link back is appreciated.
