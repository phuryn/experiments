# Managed vs non-managed agents: a 3-provider firsthand comparison

Run 2026-06-01. Same T1-T3 task battery (prime-sum, squares-mean, bat-and-ball), same deterministic graders, on each provider's hosted agent loop vs a single model call. 100% pass on every cell (tasks within model capability, so this is a cost/latency/architecture finding, not a reliability-cliff result).

## The within-provider comparison (the fair one)

Each provider tested on its own cheap/fast tier, managed/hosted loop vs one call. Cost is a token-based estimate (+ documented surcharges); treat as directional. Absolute cross-provider cost is NOT apples-to-apples (different model tiers + estimated pricing) — the *multiplier and the architecture* are the finding.

| Provider (model) | hosted/managed | single call | cost: managed vs single | latency: managed vs single |
|---|---|---|---|---|
| **Google** (gemini-3.5-flash) | Managed Agents (`/interactions`, antigravity sandbox) | `generateContent` + code_execution | **~5x more** | **~4x slower** |
| **Anthropic** (claude-haiku-4-5) | Managed Agents (`/v1/sessions`) | `messages` + code execution | **~0.5x (cheaper)** | ~1.4-2.4x slower |
| **OpenAI** (gpt-5-mini) | Responses + code_interpreter | plain Responses | **conditional** (+~$0.03 container only when code fires; else ~equal) | faster when code fires (17s vs 35s on T1), else ~equal |

## Three different architectural bets

- **Google — always-on managed sandbox.** Every interaction spins the full loop (avg 4 steps, code-exec on 61% of runs in the 225-run battery). Consistent and inspectable, but you pay a flat ~5x cost / ~4x latency even when the task is trivial.
- **Anthropic — managed loop + prompt caching.** The agent's system/tool context is cached and reused across sessions, so in steady-state the managed agent is *cheaper per run than a fresh single call*. The inverse of Google. (First run pays cache-creation; repeated use amortizes it — managed rewards volume.)
- **OpenAI — no separate managed layer.** The Responses API decides per task whether to invoke its code sandbox. gpt-5-mini solved T2/T3 by reasoning (no tool, hosted == single); on T1 it invoked code_interpreter, which is ~2x faster than plain reasoning (17s vs 35s) but adds a fixed ~$0.03 container surcharge. You pay for the sandbox only when it actually runs.

## The takeaway

"Managed agents cost more" is wrong as a universal. The managed-vs-self tradeoff is **vendor-architecture-specific**:
- pick **Google managed** when you want a consistent, inspectable sandbox loop and can eat the flat tax;
- pick **Anthropic managed** when you'll run the same agent repeatedly (caching makes it cheaper than DIY);
- with **OpenAI** there's no separate managed runtime to opt into or avoid — the Responses API conditionally runs the sandbox, so you pay only when code executes.

The portable part across all three: the agent *definition* (instructions + skills + files + tools). The runtime, and its cost curve, is a per-vendor deploy choice.

## Method / honest limits
- Models: gemini-3.5-flash / claude-haiku-4-5 / gpt-5-mini (each vendor's flash tier). Different models -> cross-provider absolute cost is indicative, not a benchmark.
- Cost = token estimate at published-tier rates (+ OpenAI code_interpreter container surcharge, + Anthropic cache pricing). Managed hosted-compute overhead beyond tokens is not fully captured -> managed cost figures are floors.
- Tasks within capability -> 100% pass everywhere; no reliability-cliff data. Long-horizon / tool-heavy tasks are the next test.
- Data: `data/runs_full.jsonl` (Google, 225), `data/anthropic_runs.jsonl` (72), `data/openai_runs.jsonl` (72). Reproducible via `scripts/`.
