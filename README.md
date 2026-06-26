# experiments

Scripts, raw logs, and results from experiments behind [Product Compass](https://www.productcompass.pm) posts. When a post claims a number, the receipt lives here.

Run by [Pawel Huryn](https://x.com/PawelHuryn). Everything is reproducible: each experiment ships the exact script, the unedited log, and a README with method, sample size, and caveats.

## Experiment sets

| Set | What it covers | Date | Source post |
|---|---|---|---|
| [fugu-ultra-vs-frontier/](fugu-ultra-vs-frontier/) | Sakana AI's fugu-ultra (a "multi-agent conductor") run through the same rigs as GLM-5.2, GPT-5.5, Opus 4.8, and Fable 5: reliability by effort (64/64), the conductor's hidden ~12x token tax, cost per run, and the planted cross-file-bug diligence test (in-context, n=10) — the conductor catches no more bugs than GPT-5.5 at ~4x the price | Jun 24, 2026 | [X: @PawelHuryn](https://x.com/i/status/2069706922027073839) |
| [frontier-vs-open-audit/](frontier-vs-open-audit/) | An open-weights model (GLM-5.2) vs the closed frontier (Opus 4.8, GPT-5.5) on a real code audit: 21 hand-planted bugs, two reasoning-effort tiers x 10 read-only runs per model (60 audits), blind-graded planted-bug recall — plus the high-vs-max effort response (a lever on the closed models, a no-op on the open one) | Jun 17, 2026 | [X: @PawelHuryn](https://x.com/PawelHuryn/status/2067324156174065677) |
| [fable-5-day-4/](fable-5-day-4/) | The day-4 retest at n=20 per cell: which launch-week claims held, flipped, or moved — plus audit economics (cost per finding), depth-10 chains, and paired nesting-cost runs | Jun 12, 2026 | [X: @PawelHuryn](https://x.com/PawelHuryn/status/2064979937543549362) |
| [fable-5-speed-depth/](fable-5-speed-depth/) | Claude Fable 5 launch week: effort dial, speed vs Opus 4.8, time-to-first-token, subagent depth, recursive workflows, nesting cost | Jun 11, 2026 | [Claude Fable 5 for PMs: The Ultimate Guide](https://www.productcompass.pm/p/claude-fable-5-guide) |
| [managed-vs-local-agents/](managed-vs-local-agents/) | Managed agent runtimes vs running the same loop yourself, across Google / Anthropic / OpenAI — all now run-by-ID over REST. 108-run clean comparison plus per-provider deep dives: local is cheaper on all three, but "managed" charges for three different things (Google taxes the sandbox even with no code, Anthropic taxes ~nothing via caching, OpenAI taxes per code-execution). Plus a Gemini↔Anthropic format translator and a one-definition-many-runtimes portability demo | Jun 1, 2026 | [Product Compass](https://www.productcompass.pm) |
| [The Silicon Gambit — LLM chess benchmark ↗](https://github.com/phuryn/lll-chess-leaderboard) | LLMs play full games through an n8n-orchestrated chess API, moves in Standard Algebraic Notation — an invalid move is an instant loss. Stateful chess.js engine, Supabase persistence, points leaderboard. Live board: [chess.productcompass.pm](https://chess.productcompass.pm/) | Dec 2025 – Feb 2026 | — |

New sets land as new top-level folders; a few live in their own repo (marked ↗). A set is one theme, not a whole model, so a model can have several sets (`fable-5-speed-depth`, `fable-5-writing-register`, ...). Newest at the top.

## Anonymization

Published files reference a private content repo through placeholders (`<WORKDIR>`, `SESSION-PROJECT-SLUG`, `<HOME>`). The exact replacement rules are checked in as code, not described in prose: [.claude/hooks/anonymize-rules.json](.claude/hooks/anonymize-rules.json), applied by [.claude/hooks/anonymize.py](.claude/hooks/anonymize.py) — which is also wired as a PostToolUse hook in [.claude/settings.json](.claude/settings.json), so Claude Code sessions working inside this repo scrub anything they write with the same rules. Nothing else is edited: numbers, timestamps, verdicts, and model-written lines are as produced.

## Reading order

1. This root README lists the sets and their dates.
2. Each set's README has a one-line headline result per experiment, plus shared method notes and caveats.
3. Each experiment folder has the full story: question, method, results, findings, caveats.
4. The logs are raw. If a number in a post and a log disagree, the log wins and I want to know: [@PawelHuryn](https://x.com/PawelHuryn).

## License

MIT. Use anything; a link back is appreciated.
