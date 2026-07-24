# bug-hunt-bench — 45 planted bugs, one real repo, six coding models

**Question:** Hide 45 subtle bugs in a real ~28K-line TypeScript codebase, keep the test suite green so nothing points at the answers, then ask each frontier coding model — in its own native agentic CLI — to find and fix as many as it can. Who actually fixes the most, and does the newest model move the needle?

**The repo:** a real VS Code / Cursor sidebar extension (an ACP client for a coding-agent CLI), ~28K lines of TypeScript. **45 bugs** live across `src/` and `media/`: **16 are real shipped bugs**, reverted straight from the repo's own fix history; the other 29 are authored in the same style (ACP wire-shape assumptions, state-machine interleavings, off-by-one card/diff matching, null handling, idempotency keyed on the wrong thing, optimistic-vs-authoritative ordering). Every one is a **runtime/logic** defect — the repo compiles clean (`tsc`) and all **922 tests pass** with every bug present (a shipped test that would have caught a planted bug had its one specific assertion neutralized). A green suite proves nothing.

**The task (identical for every model):** find and fix as many planted bugs as you can, edit the source in place, keep `tsc` clean and the suite green (do not weaken tests), and write a `BUGS_FOUND.md` report. One round per model, reasoning effort `high`, each in its native harness. The exact prompt is [prompt.md](prompt.md).

**Grading:** each model's diff vs the pristine repo is the ground truth, scored against a withheld 45-bug answer key — `FIXED_MATCH` / `FIXED_PARTIAL` / `CLAIMED_ONLY` / `MISSED`, plus any extra fixes classified genuine or false-positive.

## Scoreboard

| Model | Harness | Fixed /45 | Genuine extras | False-positive fixes | Wall | Cost (list-equiv) |
|---|---|--:|--:|--:|--:|--:|
| **GPT-5.6 Sol** | Codex CLI | **13** | 9 | 0 | 21.9 min | $10.76 |
| **Opus 5** | Claude Code | **11** | 1 | 0 | 17.4 min | $15.89 |
| **Fable 5** | Claude Code | 9 | 2 | 0 | 14.9 min | $36.42 |
| **Grok 4.5** | Grok Build CLI (ACP) | 5 | 2 | 0 | 16.5 min | $5.82 floor |
| **Kimi K3** | Claude Code / OpenRouter | 4 | 0 | 0 | 62.3 min | $9.42 |
| **Opus 4.8** | Claude Code | 2 | 0 | 0 | 17.4 min | $10.67 |

Every model left the repo healthy — `tsc` clean, 922/922 tests green, re-verified after each run. **Zero false-positive fixes across the entire field:** every extra fix any model applied was a genuine unplanted defect. **27 of the 45 bugs survived all six models.**

Per-model counts: [scoreboard.csv](scoreboard.csv). Wall-clock, tokens, and reconstructed cost: [metrics.csv](metrics.csv).

## Findings

- **Opus 5 (added launch day, July 24) is the generational-jump story: 11 vs Opus 4.8's 2** — same harness (Claude Code), same prompt, same effort. It fixed the exact two Opus 4.8 landed, plus nine harder ones, with zero false fixes. Opus 4.8's run stopped at two confirmed finds (conservative reporting); Opus 5 investigated aggressively and confirmed eleven.
- **GPT-5.6 Sol leads at 13** and effectively ran its own unplanted-bug audit on top: **9 genuine extras** nobody planted (Windows file-URI handling, a taskkill fallback, a stale client after exit, and more).
- **`media/chat.js` was near-invisible.** Only Fable and GPT landed anything there in the July run, and Kimi reviewed all of `media/` and reported nothing. Opus 5 fixed both bugs in it.
- **The compiler as a bug finder.** Opus 5 followed `tsc --noUnusedLocals` / `--noUnusedParameters` to dead call sites the planting had orphaned — which is also where its one genuine extra came from.
- **Cost is not recall.** Fable 5 wrote the sharpest diagnoses and cost the most ($36). Grok 4.5 was the cheapest arm (~$6) and the only one that spawned its own subagents. Kimi K3 was meticulous but slow — 62 minutes for 4 fixes.

## Method notes & caveats

- **n = 1 per cell.** Single round; deltas are directional, not a ranking. Planted-bug recall is unstable run to run — the same 21-bug rig at n=10 (different model set) is in [frontier-vs-open-audit/](../frontier-vs-open-audit/).
- **Native harnesses, not one fixed harness.** GPT in Codex CLI, Grok in the grok CLI over ACP, the Claude-family arms (Fable 5, Opus 4.8, Opus 5) in Claude Code, and Kimi K3 in Claude Code through an OpenRouter shim (it has no CLI of its own). By design: each model in the harness its own vendor ships.
- **"Planted" undersells a third of the set.** 16 of 45 are real shipped bugs (reverted documented fixes); models fixed those at roughly 2x the rate of the authored ones.
- **The benchmark is withheld to keep it usable.** The **answer key, the seeded source, and the per-model fix diffs are not published** — publishing them would burn the benchmark. The scoreboard, metrics, and the exact prompt are here; the prompt is a self-contained spec.
- **Opus 5 ran on launch day (July 24), same price as Opus 4.8** ($5 / $25 per Mtok). The other five ran July 19.
- **Cost is list-equivalent**, reconstructed per arm. Grok's is a floor — its CLI reports context *fill*, not cumulative *bill* (the token-accounting defect written up in [five-models-three-harnesses/](../five-models-three-harnesses/)). Don't rank costs across differently-metered arms to the dollar.
- **De-identified.** The app is a real, public VS Code extension; private working paths are scrubbed. Numbers, timestamps, and verdicts are as produced.

## Source post

[@PawelHuryn on X](https://x.com/PawelHuryn/status/2078834615519731832) — the five-model run. Opus 5 column added July 24, 2026.

## License

MIT. Use anything; a link back is appreciated.
