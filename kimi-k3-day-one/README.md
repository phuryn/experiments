# Kimi K3: Day One (July 16–18, 2026)

Moonshot shipped **Kimi K3** on July 16, 2026 — 2.8 trillion parameters, the largest open-weight model released to date. This set is the receipts behind one claim: **it matches the frontier in my tests, and you probably cannot use it yet.**

Three experiments. The first asks whether it is any good. The second asks whether the first question was even measurable on day one. The third closes the arc: the cell that never finished ran clean on day 3, with nothing changed but the date.

K3 is a **sixth arm bolted onto an existing rig**: the same 8 tasks, answer keys and grading as [five-models-three-harnesses/](../five-models-three-harnesses/) (Jul 10, 2026). The four comparison columns here are that set's numbers, not re-runs. Read it first for the full method, the per-model characters, and the token-accounting defect. Two things K3 changes about its conclusions: that set found **zero false positives from any arm** — K3 is the first to post any (2) — and it took the planted-bug crown off Opus (14 vs 12). Grok 4.3 is dropped here; the other four columns are unchanged.

| # | Experiment | Question | Headline result |
|---|---|---|---|
| [01](01-eight-task-scoreboard/) | Eight-task scoreboard | Does K3 match Opus 4.8, GPT-5.5, GPT-5.6 Sol and Grok 4.5 on a real codebase? | Matched or beat all three frontier models on **6 of the 7 tasks it finished**; caught **14 of 21 planted bugs vs Opus's 12**, the best in the field — and was the only model to report bugs that were not there (2 false positives) |
| [02](02-day-one-capacity/) | Day-one capacity | Two cells never finished on launch night. Was that the model? | **No.** The same implement cell returned **0 tokens on launch night and 14/14 thirteen hours later** — same model, same task, same prompt, only the clock changed. A day-one benchmark is partly measuring queue depth |
| [03](03-day-three-recovery/) | Day-three recovery | The stale-docs cell died five times. Does it ever finish? | **Yes — on day 3, with nothing changed but the date:** 68 min, clean exit, **zero rate-limit events** through the same proxy that absorbed **162** the day before. Scored **3/5 plants + 29 extra findings, 29/29 verified genuine, 0 false positives** |

## Method notes & caveats

- **n=1 per cell.** Directional, not a ranking. The same 21-planted-bug rig at n=10 (different model set) is in [frontier-vs-open-audit/](../frontier-vs-open-audit/), and it shows recall is unstable run to run. Read single-run task scores with that in mind.
- **Three native harnesses, not one.** Opus 4.8 in Claude Code CLI, both GPT arms in Codex CLI, Grok 4.5 in grok CLI. K3 has no agentic CLI of its own, so it borrowed Claude Code's through an Anthropic-API shim to OpenRouter. Only K3 and Opus shared a harness. This compares models in native agentic harnesses, not in a fixed one.
- **K3 alone ran on launch-day infrastructure.** The other four ran on stable, unthrottled surfaces. That is not an equal test surface, and experiment 02 is about exactly that asymmetry.
- **One cell was DNF through day 2, not zero.** K3 never finished the stale-docs audit across five attempts on July 16–17. It was reported as missing, because scoring a throttle as a model failure would be wrong. **Resolved July 18:** the cell ran clean on day 3 and scored — [03-day-three-recovery](03-day-three-recovery/). The day-one scoreboard in 01 keeps the DNF as the day-one snapshot; 03 carries the final cell.
- **This set expires.** The throttle numbers describe July 16–18, 2026. Moonshot's capacity will move; that is the finding, not a flaw.
- **De-identified.** One real private app. Raw per-run model reports quote the repo and are **withheld**; the CSVs, grades and logs published here are content-free. Answer keys and seeded source are not published. Task prompts are self-contained specs and are published verbatim.
- **Cost:** K3 figures are OpenRouter-metered at K3's list rate ($3/M in, $15/M out, $0.30/M cache read — the same headline rate as Opus 4.8). Do not rank them against natively-metered arms; cache accounting differs and that comparison is exactly how you get a 25x error.

## Source post

[@PawelHuryn on X](https://x.com/i/status/2078039188834783367)

## License

MIT. Use anything; a link back is appreciated.
