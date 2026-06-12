# Fable 5: Day-4 Retest (June 11–12, 2026)

The launch-week numbers in [fable-5-speed-depth/](../fable-5-speed-depth/) were collected on 3–10 rounds per cell, on a build Anthropic was tuning daily. This set is the retest: **20 rounds per cell on a single build** (Claude Code CLI 2.1.173, June 12; the n=10 warm-up rounds from June 11, CLI 2.1.168, are included as separate CSVs and never pooled). Some launch-week claims held. Some flipped. The flips are listed below, not hidden.

| # | Experiment | Question | Headline result |
|---|---|---|---|
| [01](01-effort-dial-n20/) | Effort dial, n=20 | Does `--effort` change speed or quality? | Dial bites only when the task needs it; every graded hard-puzzle answer correct at every level; `max` is the only level where Fable and Opus separate (60.8s vs 49.0s med) — and it moves build to build |
| [02](02-repo-questions-and-audits-n20/) | Repo questions + heavy audits, n=20 | What does Fable cost in time on trivial vs real work? | Trivial: 1.48x. Heavy 3-file audits: **1.29x median** [0.92–1.70] — the launch-week "parity on real work" claim flipped |
| [03](03-ttft-tokens-n20/) | TTFT + token counts, n=20 | Where does the "slow" feeling come from? | Starting pause held: first sign of life med 6.7s vs 4.3s. Token claim flipped: the launch-day 40% token gap shrank to 8%, and Fable finishes the same math problem 1.5x behind |
| [04](04-audit-economics/) | Audit economics | What does a real finding cost? | Per audit 2.5x ($2.93 vs $1.17). Per finding 1.25x (med 14 vs 7 findings). Per the one deep cross-file bug: **0.25x** — Fable caught it 20/30, Opus 2/30, so expected spend per catch is $4.40 vs $17.55 |
| [05](05-depth-chains/) | CLI depth chains | Is there a platform wall on CLI-composed nesting? | No wall at depth 6 (10/10, 49–57s) and none at depth 10 (10/10, 84–93s). The depth-5 cap applies to Task-tool subagents only |
| [06](06-recursive-workflows/) | Recursive workflows | Can each level author the next level's orchestrator? | Yes, repeatedly: depth-6 spec 11/11, Node variant 10/10, and depth-10 ladders where the models wrote 90+ orchestrators with zero refusals |
| [07](07-nesting-cost/) | Nesting cost, paired | What does depth cost vs a flat fan-out? | **2.54x median cost ratio** [1.25–3.42] over 7 strictly-paired runs — the launch-week 1.6–1.8x estimate was too kind. Nested never came out cheaper; it did once finish faster |

## What flipped vs launch week

| Launch-week claim ([fable-5-speed-depth](../fable-5-speed-depth/)) | Day-4 result at n=20 |
|---|---|
| Speed: "parity on real multi-step work" | **1.29x median time tax** on heavy audits [0.92–1.70] — the tax flattens with task size, it doesn't vanish |
| Tokens: "~40% fewer output tokens, finishes sooner" | **8% fewer tokens, finishes 1.5x behind** — both models now write 2–3x more tokens than their own launch-day logs |
| Nesting cost: "1.6–1.8x" | **2.54x median** over 7 paired runs |
| Speed trivial: "~1.6x" | 1.48x — held |
| TTFT: "starts ~3s later" | 2.4s later (med 6.7s vs 4.3s) — held |
| Depth: "6 levels, no wall" | extended to **10 levels, still no wall**, both for CLI chains and recursive self-authoring workflows |

The meta-finding: **day-one benchmarks age in days.** The build is tuned daily; absolute numbers rot, ratios travel better, and even ratios deserve a retest.

## Method notes & caveats

- **Effort levels: matched, not default.** This machine had `effortLevel: xhigh` persisted in Claude Code settings, and CLI precedence (env var > configured level > model default) means every flag-less run used it — for **both** models, so the ratios stand, but the honest label is "matched effort (xhigh)", not "out-of-box default" (the documented default is `high` on both Fable 5 and Opus 4.8). Verified empirically: flag-less runs match the explicit-xhigh distribution (med ~19s on the easy question vs 18.5s xhigh, 13.6s high). Bonus finding: `--effort <any garbage string>` silently falls back to the *configured* level, not the model default — a typo in `--effort` runs at whatever your settings say (see [01](01-effort-dial-n20/), the `xyz` control: n=20, med 17.6s).
- **Harness:** `claude -p`, subscription surface, write tools disallowed for timed runs, wall-clock includes CLI startup. Timed sets ran in 3 matched lanes (threads) over a fixed-seed shuffled run list, so no model or level got a slower slot. First-token traces ran strictly serial. Outliers kept, never trimmed; failed runs stay in the CSVs with their `rc`.
- **Costs** are computed two ways where available: the CLI's own `total_cost_usd`, and usage × public API prices (Fable $10/$50, Opus $5/$25 per MTok; cache write ×1.25, cache read ×0.1) — they agree to the cent (see [04](04-audit-economics/)).
- **Anonymization (full disclosure):** the published copy replaces the local checkout path with `<WORKDIR>` and the local Claude session-log folder slug with `SESSION-PROJECT-SLUG`, in scripts *and* in model-generated artifacts/logs. Nothing else was edited; every number, timestamp, pass/fail verdict, and model-written line is as produced. The replacement rules are checked in as code at [.claude/hooks/](../.claude/hooks/) and wired as a PostToolUse hook for any Claude Code session in this repo.
- **What's excluded:** `answers/` (raw model answer bodies — they quote a private content repo) and the per-run output dirs of experiment 07 (model analyses of a private posts dataset). The content-free CSVs, harnesses, and verdict logs for both are included. Tasks reference files in that private repo by path; prompts are quoted verbatim in the scripts, so you can rebuild equivalents against any repo.
- Subscription surface; API latencies may differ. Single build (2.1.173) for all v4 rows; expect drift on later builds.

## License

MIT. Use anything here however you like; a link back is appreciated.
