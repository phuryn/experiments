# managed-vs-local-agents — managed agent runtimes vs running the loop yourself, across Google / Anthropic / OpenAI

All three frontier vendors now expose a persistent agent/workflow you invoke by ID over REST (yes, OpenAI too: `POST /v1/workflows/{id}/run`). So this set benchmarks each managed runtime against running the *same* agent loop on my own machine — same tasks, same model per provider, code executing locally for free in the local arm. Plus a Gemini↔Anthropic format translator and a portability demo: one agent definition running unchanged on multiple runtimes.

The surprise wasn't that managed costs more. It's that "managed" charges for **three completely different things**: **Google taxes the sandbox** (~5.3x, even on a task that runs no code), **Anthropic taxes ~nothing** (~1.2x, caching absorbs it — and managed is *cheaper* than a single call), **OpenAI taxes the code** (≈ local on reasoning, +$0.03 flat container fee only when it actually runs code). Same agent, same tasks, 108 runs in the clean comparison, all logged. The portable constant across all of it is the agent definition.

## First: "managed agent" means three different things

Most comparisons skip this. The providers are not offering the same thing.

| Provider | What "managed" actually is |
|---|---|
| **Google** — Managed Agents (`/v1beta/interactions`) | A real managed runtime. Register an agent; Google provisions a Linux sandbox and runs the **entire multi-step loop** server-side (reason → call tool → run code → observe → repeat → answer). One request, every step. Persistent agents, sessions, environments. |
| **Anthropic** — Managed Agents (`/v1/agents` + `/v1/sessions`) | Also a real managed runtime. A container per session, the full loop on Anthropic's orchestration layer, streamed events. Plus success-criteria graders, a Vaults secrets API, and subagents. |
| **OpenAI** — Agent Builder workflow, headlessly runnable by ID | **Agent Builder** (AgentKit) publishes a workflow as a persistent, OpenAI-hosted, versioned object (`wf_...`). Callable headless: **`POST /v1/workflows/{id}/run`**, header `OpenAI-Beta: workflows=v1`. Gotcha that cost a day: set the workflow variable (`input_as_text`) in the body alongside `input`, and `stream: true`, or `result.output` comes back null. Also reachable via ChatKit and exportable as Agents SDK code. The stateful Assistants API is deprecated (sunset 2026-08-26). |

So the OpenAI arm here is the **real hosted Agent Builder workflow** (`wf_68f0aace...`), not a Responses proxy. All three are apples-to-apples managed run-by-ID loops.

## Experiments

| # | Experiment | Question | Headline result |
|---|---|---|---|
| 1 | Managed vs local loop (clean, 3 providers) | Does a managed runtime cost more than running the same loop yourself? | Local is cheaper on all three, but the *margin* is vendor-specific: **Anthropic ~1.2x, Google ~5.3x, OpenAI ~16.4x avg** (N=6/cell, 108 runs). |
| 2 | What "managed" actually charges for | Same averages — but who taxes what, per task? | **Google taxes the sandbox** (flat, 2.9x even on a no-code task), **Anthropic ~nothing** (caching), **OpenAI per code-execution** (+$0.03 only when the container fires). |
| 3 | Anthropic: managed vs single call | Is the managed runtime a tax over one API call? | **No — managed is 0.4–0.5x the cost of a single call** (N=12). Context auto-caching makes the hosted loop *cheaper* than calling the model raw. |
| 4 | OpenAI: hosted Agent Builder workflow | Is the workflow really headless-runnable by ID? | **Yes**, via `POST /v1/workflows/{id}/run`. Cost ≈ a single call on reasoning tasks; only T1 (code) carries the ~$0.03 container fee (N=12). |
| 5 | Google: managed vs self-orchestrated battery | How big is the sandbox tax at scale? | **~5–8x cost, ~4x latency** across T1–T3 (N=25/cell, 225 runs), 100% pass everywhere. The tax is the always-on sandbox, not the tokens. |
| 6 | Portability (one definition, many runtimes) | Does one agent definition run unchanged across providers? | The same `SKILL.md` + files caught the same planted bug on **Google's cloud sandbox and on Claude locally**; one `AGENTS.md` format rule was obeyed **100%** across Google Managed Agents, Gemini direct, and Claude. |
| 7 | Translator (Gemini ↔ Anthropic) | Can one agent definition cross vendor formats with a thin adapter? | **4/4 pass.** Text, system, tools, tool-calls, tool-results all translate both directions with a stateless REST adapter. The control surface is portable; only the runtime differs. |
| 8 | Google advanced primitives | Which of skills / MCP / secrets / subagents actually work today? | **Custom `SKILL.md`: PASS.** MCP `tools[]`: rejected on the dev endpoint (Enterprise/Vertex-only). Egress-proxy secrets: timed out / inconclusive. Subagents: not exposed as a step type. |

**Headline result (the tweet):** *All three frontier vendors now run your agent by ID over REST. Running the loop locally was cheaper on all three — but "managed" charges for three different things: Google taxes the sandbox (~5x even with no code), Anthropic taxes ~nothing (caching makes managed cheaper than a raw call), OpenAI taxes the code ($0.03/container, nothing otherwise). The portable constant is the agent definition.*

## Shared method

- **Tasks (T1–T3).** T1 prime-sum (deterministic compute, rewards running code), T2 mean-of-squares (mixed — solvable in reasoning or code), T3 bat & ball (pure reasoning, no code). T4 (Google battery) is the portability task. All tasks are within model capability, so every cell hit **100% pass** — this is a cost/latency/architecture finding, **not** a reliability-cliff result.
- **Models.** Anthropic `claude-haiku-4-5`, Google `gemini-3.5-flash`, OpenAI `gpt-5-mini`. Cheap tiers on purpose — the architecture, not the model, is the variable.
- **Arms.** MANAGED = the provider runs the whole loop in its sandbox by ID. LOCAL = I run the loop here (base model API per step + Python executing locally on free CPU). For Anthropic/OpenAI the per-provider deep dives also compare against a single non-agentic call.
- **Cost.** Token-based estimate at each vendor's published tier rates (gemini-3.5-flash, claude-haiku-4-5 $1/$5 per 1M, gpt-5-mini ~$0.25/$2.00 per 1M), **plus** OpenAI's `code_interpreter` container fee (~$0.03/run when it fires) and Anthropic managed cache pricing. Not from invoices. Hosted-compute overhead that isn't in the token bill is not captured, so a managed cost is a *floor*.
- **Caching reported as-used.** Managed runtimes auto-cache a large agent context; the local loop's context is lean. Both reported as actually billed — this is part of why managed-Anthropic comes out cheap, and it's a real property of the runtime, not a thumb on the scale.
- **Run 2026-06-01.** OpenAI arm = the real hosted Agent Builder workflow `wf_68f0aace...` via `POST /v1/workflows/{id}/run`, streamed for usage/output (see [FINDINGS.md](FINDINGS.md) §K-v2 / §L).

### Experiment 1 — managed vs local loop (clean, 3 providers, N=6/cell)

From [outputs/comparison-clean.md](outputs/comparison-clean.md) / [data/clean_runs.jsonl](data/clean_runs.jsonl). 108 runs total, **total estimated cost $0.3745**:

| Provider | managed $ | local $ | cost x | managed lat | local lat | lat x |
|---|---|---|---|---|---|---|
| anthropic | $0.00255 | $0.00221 | **1.2x** | 5.99s | 2.12s | 2.8x |
| google | $0.00403 | $0.00077 | **5.3x** | 12.3s | 2.88s | 4.3x |
| openai | $0.01060 | $0.00065 | **16.4x** | 6.69s | 5.78s | 1.2x |

Every cell: 100% pass.

### Experiment 2 — what "managed" charges for (the average is misleading)

The OpenAI 16.4x is one code-firing task dragging up two near-free ones. Broken out by task (managed/local cost ratio + whether the agent actually ran code):

| Task | runs code? | Google | Anthropic | OpenAI |
|---|---|---|---|---|
| T1 prime-sum | yes (all 3) | 7.0x | 1.3x | **~65x** ($0.0306 vs $0.0005) |
| T2 mean-of-squares | Google yes; OpenAI/Anthropic no | 8.0x | 1.6x | **~1.0x** |
| T3 bat & ball (pure reasoning) | none | **2.9x** | 0.7x | **~0.6x** (cheaper) |

- **Google = sandbox tax.** ~5x on average, still **2.9x on T3 where no code runs at all.** You rent an always-on sandbox and pay whether the agent executes anything or not.
- **Anthropic = ~no tax.** ~1.2x, *cheaper* than local on T3. Auto-caching of the agent context absorbs the managed overhead.
- **OpenAI = code tax.** == local (sometimes cheaper) on reasoning; +$0.03 flat container fee only when `code_interpreter` fires. The model decides whether to run code (gpt-5-mini solved T2/T3 in reasoning, fired the container only on T1), so OpenAI's managed cost is workload-dependent, not fixed.

### Experiment 3 — Anthropic: managed vs single call (N=12/cell)

From [outputs/phase-anthropic.md](outputs/phase-anthropic.md) / [data/anthropic_runs.jsonl](data/anthropic_runs.jsonl). **Total this run $0.2785**:

| Task | managed $ | single $ | cost x | managed lat | single lat |
|---|---|---|---|---|---|
| T1 | $0.00301 | $0.00600 | **0.5x** | 6.69s | 4.79s |
| T2 | $0.00297 | $0.00542 | **0.5x** | 6.72s | 3.95s |
| T3 | $0.00157 | $0.00424 | **0.4x** | 4.55s | 1.88s |

The managed loop is *cheaper than a single raw call* on this model — caching absorbs the loop overhead. Managed runs slower (the hosted loop adds latency), but not more expensive.

### Experiment 4 — OpenAI: hosted Agent Builder workflow vs single (N=12/cell)

From [outputs/phase-openai.md](outputs/phase-openai.md) / [data/openai_runs.jsonl](data/openai_runs.jsonl). **Total this run $0.4508**:

| Task | hosted $ | single $ | hosted uses code_interpreter? |
|---|---|---|---|
| T1 | $0.03058 | $0.00493 | 100% (container fee) |
| T2 | $0.00067 | $0.00065 | 0% |
| T3 | $0.00044 | $0.00030 | 0% |

The hosted workflow tracks a single call on the reasoning tasks; the gap is entirely the ~$0.03 `code_interpreter` container fee on T1.

### Experiment 5 — Google: managed vs self-orchestrated battery (N=25/cell, 225 runs)

From [outputs/phase-run_full.md](outputs/phase-run_full.md) / [data/runs_full.jsonl](data/runs_full.jsonl). Arm A = Google Managed Agents, Arm B = self-orchestrated local loop, Arm C = portability baseline (T4 only). **Total this run $0.5743**, every cell 100% pass:

| Task | A (managed) $ | B (local) $ | A lat | B lat |
|---|---|---|---|---|
| T1 | $0.00486 | $0.00085 | 12.8s | 3.11s |
| T2 | $0.00414 | $0.00065 | 12.03s | 2.77s |
| T3 | $0.00318 | $0.00092 | 12.01s | 3.22s |
| T4 (portability) | $0.00775 | $0.00044 | 16.04s | 1.59s |

### Experiment 6 — portability (one definition, many runtimes)

A single agent **definition** (instructions + `SKILL.md` + files, in [anthropic-local/](anthropic-local/)) ran on Google's managed cloud sandbox **and** on Claude locally and caught the same planted bug ([outputs/phase-explore-google.md](outputs/phase-explore-google.md): `found_mul_bug=True, ran_code=True`). One `AGENTS.md` format rule was obeyed **100%** across Google Managed Agents, Gemini direct, and Claude. The portable thing is the definition; the runtime is a deploy choice.

### Experiment 7 — translator (Gemini ↔ Anthropic), 4/4

From [outputs/phase-translator.md](outputs/phase-translator.md) / [data/translator_tests.json](data/translator_tests.json). A thin **stateless REST adapter** translates request/response (text, system, tools, tool-calls, tool-results, config, finish/stop, usage) both directions: Gemini `functionDeclarations` ↔ Anthropic `tools`/`input_schema`, `functionCall` ↔ `tool_use`, `functionResponse` ↔ `tool_result`. **Out of scope:** it does *not* reproduce Google's managed runtime (loop + sandbox) — that's a harness to build, not a format to translate.

### Experiment 8 — Google advanced primitives (firsthand retest)

From [outputs/phase-advanced.md](outputs/phase-advanced.md), against the live Gemini API Managed Agents dev endpoint, 2026-06-01:

| Primitive | Result | Detail |
|---|---|---|
| Custom `SKILL.md` | **PASS** | skill applied (HAIKU output produced) |
| Secrets via egress proxy | FAIL-run | read operation timed out |
| `tools[]` incl. `mcp_server` (dev endpoint) | REJECTED | dev endpoint 400: only `google_search`, `url_context`, `code_execution` supported (MCP may be Enterprise/Vertex-only) |
| Subagents | NOT-EXPOSED | no sub-agent/agent-spawn step type observed |

## Findings

1. **Managed is now run-by-ID on all three — including OpenAI.** The hosted Agent Builder workflow is genuinely headless via `POST /v1/workflows/{id}/run`; the only blockers were access (project-matched key) and input wiring (`input_as_text` in the body + `stream:true`), both documented in FINDINGS.
2. **Running the loop locally was cheaper on all three — but the margin is the story, not the direction.** Anthropic ~1.2x, Google ~5.3x, OpenAI ~16.4x average. Three different pricing bets, not one "managed premium."
3. **"Managed" charges for three different things.** Google taxes the always-on sandbox (flat, even when no code runs); Anthropic taxes ~nothing (caching, managed is *cheaper* than a single call); OpenAI taxes per code-execution (~$0.03 container fee, nothing on pure reasoning). Read the per-task table, not the average.
4. **The model decides OpenAI's managed cost.** gpt-5-mini ran the container only on T1 and solved T2/T3 in reasoning — so OpenAI's managed cost is workload-dependent, not a fixed runtime tax.
5. **The portable constant is the agent definition.** The same definition caught the same bug on Google's sandbox and on Claude local; one `AGENTS.md` rule held 100% across three runtimes; the format translator round-trips tool definitions both ways. The control surface is portable; the runtime is a deploy choice.

## Caveats

- **Within-capability tasks → 100% pass everywhere.** This is a cost / latency / architecture finding, **not** a reliability-cliff result. Nothing here says one runtime is more *correct* than another.
- **Costs are token-based estimates at published tier rates**, not invoices — plus OpenAI's `code_interpreter` container fee and Anthropic cache pricing. Hosted-compute overhead not reflected in tokens is uncaptured, so a managed cost is a **floor**.
- **Caching is reported as-used.** Managed runtimes auto-cache a large agent context; the local loop's context is lean. This is real and load-bearing for the Anthropic result — a different context shape would move the ratio.
- **Sample sizes vary by experiment** (N=6 clean / N=12 per-provider / N=25 Google battery) and are labeled per table. Latency includes the managed loop's server-side roundtrips; prefer the cost *ratios* over absolute seconds.
- **Advanced-primitive results are dev-endpoint, single-shot, 2026-06-01.** MCP rejection and the secrets timeout may be endpoint/tier-specific (Enterprise/Vertex), not capability limits. Directional.
- **Resource IDs are receipts, not secrets.** The `wf_…` / `agent_…` / Google interaction IDs in the scripts and logs are account-scoped identifiers, useless without the corresponding API key. Numbers, timestamps, and verdicts are as produced.
- Numbers here are read straight from the raw logs in [data/](data/). If a number here and a post disagree, the log wins and I want to know: [@PawelHuryn](https://x.com/PawelHuryn).

**Files:** `README.md`, `FINDINGS.md` (durable running log of every test + correction), `requirements.txt`, `.env.example`, `scripts/` (`clean_comparison.py`, `runner.py`, `anthropic_managed_runner.py`, `anthropic_managed_smoke.py`, `openai_runner.py`, `translator.py`, `probe_advanced.py`, `explore_codedef.py`, `anthropic_local_agent.py`, `gemini_client.py`, `analyze.py`), `data/` (raw per-run logs + API responses — the receipts), `outputs/` (human-readable phase reports), `anthropic-local/` (the portable code-defined agent definition: `CLAUDE.md` + `.claude/skills/bug-finder/SKILL.md` + `spec.md` + `solution.py`).

**Reproduce:** `pip install -r requirements.txt`, copy `.env.example` → `.env` and add `GEMINI_API_KEY` (Managed Agents preview), `ANTHROPIC_API_KEY` (managed-agents beta), `OPENAI_API_KEY`. Then e.g. `python scripts/clean_comparison.py --n 6` (the headline; set `OAI_WORKFLOW_ID` to your own `wf_...`). Full per-script guide in [FINDINGS.md](FINDINGS.md).

**Source post:** [Product Compass](https://www.productcompass.pm) — Paweł Huryn.
