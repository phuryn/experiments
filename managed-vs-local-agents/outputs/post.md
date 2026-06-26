<!--
Post drafted from the firsthand experiment in experiments/managed-agents/ (225 runs, 2026-06-01).
Lane C (original builder-teacher take). One thesis: the runtime is rented; the artifact layer is the asset.
Extends the "Review Artifacts, Not Code" article (L1 harness, L10 portable layer, Lesson 6).
Real numbers only. No emoji, no em dash. Gate: builder-teacher, verdict-last, specificity, soundbite closer.
Honest caveat baked in: tasks were within-capability (100% everywhere), so this is a cost/control/portability
finding, NOT a reliability-cliff claim.
-->

# X (Note Tweet) - primary

I ran 225 executions on Google's new Managed Agents.

It's their one-API-call agent runtime: you POST a task, Google spins up a Linux sandbox, runs the whole agent loop, hands back the result. The question I wanted answered: when Google runs the loop for you, what is actually still yours?

I ran the same task battery three ways. Google's Managed Agents. The same model, self-orchestrated, where I run the loop. And Claude.

The runtime is a rental. Same model, same 100% pass rate, but handing Google the loop cost about 5x more and ran about 4x slower than orchestrating it myself. You are renting a sandbox and a loop. Worth it when the task needs them. Pure overhead when it doesn't.

The control surface is portable. I wrote one AGENTS.md, a simple format rule, and fed it to all three: Google's managed agent, Gemini direct, and Claude. 100% obeyed it. Same behavior across two vendors and a managed runtime.

Then I built a Gemini-to-Anthropic translator and ran the same agent definition on both providers. It works.

So the runtime is rented and locked to one vendor. The AGENTS.md is yours and runs anywhere.

Rent the runtime if it saves you time. Just don't confuse it with the asset. The artifact layer is the asset.

---

# LinkedIn - variant

I ran 225 agent executions on Google's newest API.

Google just shipped Managed Agents: one API call, they spin up a Linux sandbox, run the whole agent loop, hand back the result. No orchestration code. I wanted to know what you actually keep when you let the vendor run the loop.

So I tested the same task battery three ways: Google's Managed Agents, the same model self-orchestrated (I run the loop), and Claude.

Two things came back clearly.

1. The managed runtime is a rental.
Same model. Same 100% pass rate. But handing Google the loop cost ~5x more and ran ~4x slower than orchestrating it myself. You're renting a sandbox and a loop. Real value when the task needs them. Pure overhead when it doesn't.

2. The control surface is portable.
I wrote one AGENTS.md, a single format rule, and fed it to all three runtimes: Google's managed agent, Gemini direct, and Claude. Every one obeyed it, 100%. The same markdown steered two different vendors and a managed runtime identically.

Then I built a Gemini-to-Anthropic translator and ran the same agent definition on both providers. It works.

The runtime is rented and locked to one vendor. The AGENTS.md is yours, and it runs anywhere.

This is the whole argument from my last piece, now with a new vendor's product as the proof: you don't own the runtime. You own the artifact layer. Rent the runtime if it saves you time. Just don't mistake it for the asset.

(225 runs, fully reproducible, cost me 57 cents. The harness, the translator, and the data are in a repo.)

---

# Notes
- Honest scope: every cell hit 100% because the tasks were within model capability. This is a cost / control / portability finding, not a reliability-cliff claim. A reliability test needs harder, long-horizon, tool-heavy tasks (next experiment).
- Numbers: 225 runs; cost multiplier avg 5.2x (5.7 / 6.4 / 3.4); latency multiplier avg 4.0x (4.1 / 4.3 / 3.7); AGENTS.md compliance 100% on all three runtimes; translator 4/4 live tests; total est. cost $0.57.
- Connects to: "Review Artifacts, Not Code" (Lesson 6 - point every agent at one source of truth; L10 portable knowledge layer; L1 the harness is the leverage).
