# The shrink is frontier-tier only (cross-model, same day)

The [parent finding](../README.md) measured Opus's system prompt shrinking April → July. This folder answers the next question: **do all Claude models get the shrunk prompt, or just some?**

Answer: **just the frontier.** Run each model through Claude Code on the same machine, same day, and there are exactly **two** base prompts in play — and which one you get is decided by capability tier.

## Result

| Model | Base prompt (words) | Version | Captured |
|---|---|---|---|
| Opus 4.7 (Apr 2026) | 1,918 | OLD / verbose | transcript |
| Sonnet 4.6 (Apr 2026) | 1,918 | OLD / verbose — identical to Opus 4.7 | transcript |
| Sonnet 5 (Jul 2026) | **2,094** | OLD / verbose — every "don't" rule (`# Doing tasks`, `# Tone and style`) | proxy |
| Haiku 4.5 (Jul 2026) | **2,094** | OLD / verbose — **byte-identical to Sonnet 5** | proxy |
| Fable 5 (Jul 2026) | 901 | NEW / lean (`# Harness`) | proxy |
| Opus 4.8 (Jul 2026) | 383 | NEW / lean (`# Harness`) | proxy |

*April numbers are transcripts (ex-memory base prose); July numbers are proxy-captured (exact). The two capture methods aren't word-for-word comparable, but the **version** column — verbose vs lean — is method-independent, and that's the real split.*

### Diffs

Unified diffs of the base prose. On the temporal ones (old → new), the *old* side is an April transcript and the *new* side a headless proxy capture, so the opening-line and minor formatting differences are capture-mode artifacts, not prompt changes; the substantive change is verbose vs lean.

| Comparison | What it shows |
|---|---|
| [Opus 4.7 → Opus 4.8](diff-opus-4-7-to-4-8.diff) | the frontier shrink over time: verbose → lean |
| [Opus 4.7 → Fable 5](diff-opus-4-7-to-fable-5.diff) | old top model → new frontier: verbose → lean |
| [Sonnet 4.6 → Sonnet 5](diff-sonnet-4-6-to-5.diff) | the workhorse prompt **grew** (1,918 → 2,094) and stayed verbose — it did NOT shrink |
| [Opus 4.8 vs Fable 5](diff-opus-4-8-to-fable-5.diff) | the two current frontier prompts, both lean (Fable carries an extra Mythos/identity block) |
| [Opus 4.8 vs Sonnet 5](diff-opus-4-8-vs-sonnet-5.diff) | the current tier split: lean vs verbose, same day |
| Haiku 4.5 vs Sonnet 5 | identical — no diff; compare [`haiku-4-5.txt`](haiku-4-5.txt) and [`sonnet-5.txt`](sonnet-5.txt) directly |

Two findings fall out:

1. **The lean prompt is frontier-only.** Opus 4.8 and Fable 5 get the stripped `# Harness` version. Sonnet 5 and Haiku 4.5 still run the full 2,094-word rulebook — "don't add abstractions," "don't add error handling," "don't write comments," the lot. Opus 4.8's base prompt (383 words) is **~82% smaller** than the prompt Sonnet 5 and Haiku 4.5 still receive.
2. **Sonnet 5 and Haiku 4.5 share one prompt.** Their base prose is identical (the only per-model bytes — model ID, knowledge cutoff — live in the `# Environment` section, excluded here). Same pattern as the April Opus-4.7/Sonnet-4.6 finding: one shared prompt, tiny per-model patches.

And temporally (using the April transcripts in the parent folder as the "before"):
- **Opus shrank:** April 4.7 (verbose) → July 4.8 (lean).
- **Sonnet did not:** April 4.6 (verbose) → Sonnet 5 today (still verbose, 2,094).

So "smarter models need fewer instructions" isn't a slogan Anthropic said once — it's a live split across the current lineup. The most capable models get the least scaffolding.

## Method

Captured from the **actual outgoing API request**, not the model's self-report. A local endpoint set via `ANTHROPIC_BASE_URL` logs the request body the Claude Code harness sends; the model never has to cooperate and can't paraphrase:

```
ANTHROPIC_BASE_URL=http://127.0.0.1:PORT claude -p --model <id> "ok"
# read the "system" field out of the logged request body
```

All four captured this way, headless (`claude -p`), same repo, same day. Counts are the **Anthropic-shipped base prose only** — from the first line to just before `# Environment`. Tool schemas, MCP config, skills, CLAUDE.md, and all session/environment sections are excluded on every model (they're injected separately and vary by session).

Two method notes worth recording:
- **Self-reports undercount.** Asked to reproduce their own prompt, Haiku returned 2,181 words (true: 2,538 full / 2,094 base) and Fable returned 988 (true: 1,574 full / 901 base). Models do not reproduce their own instructions in full — only the request capture is trustworthy. (Self-report and proxy give consistent *ratios*, though: Fable/Opus ≈ 1.9× either way.)
- **Running an old model ID today does not recover its old prompt.** `claude --model claude-opus-4-7` in today's CLI returns today's verbose prompt (2,094 base), not April's. The harness is current; only the weights are old. The only real record of the April prompts is the transcripts in the parent folder.
- **Sonnet 5 refused to self-report its prompt** — the one model of the four that declined. Nothing in its system prompt forbids sharing it (grepped: the only near-match is a git-safety line about not committing secrets). The refusal is a model-level behavior, not an instruction. The proxy captured it anyway.

## Files

- `opus-4-8.txt`, `fable-5.txt`, `sonnet-5.txt`, `haiku-4-5.txt` — July base prose per model (proxy-captured, headless, stripped at `# Environment`).
- `april-opus-4-7.txt`, `april-sonnet-4-6.txt` — the April base prose (transcribed; the only surviving record of the old prompts).
- `diff-*.diff` — the five comparisons in the Diffs table above (Haiku vs Sonnet omitted — identical, no diff).
