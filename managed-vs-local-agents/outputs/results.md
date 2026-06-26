# Results: Testing Google's Managed Agents (Gemini API)

Run 2026-06-01. 225 total executions. Graders are deterministic (objective answers), not model-judged. Cost is estimated from token counts (directional).

## 1. Reliability, cost, latency by task and arm

Arm A = Google Managed Agents (they run the loop). Arm B = self-orchestrated gemini-3.5-flash (I run the loop). Same model class.

| Task | Arm | N | Pass% | Median latency | Avg cost (est) | Median steps (A) | % used code-exec (A) |
|------|-----|---|-------|----------------|----------------|------------------|----------------------|
| T1 | A | 25 | 100% | 12.8s | $0.00486 | 5 | 100% |
| T1 | B | 25 | 100% | 3.11s | $0.00085 | - | 0% |
| T2 | A | 25 | 100% | 12.03s | $0.00414 | 4 | 88% |
| T2 | B | 25 | 100% | 2.77s | $0.00065 | - | 0% |
| T3 | A | 25 | 100% | 12.01s | $0.00318 | 2 | 0% |
| T3 | B | 25 | 100% | 3.22s | $0.00092 | - | 0% |
| T4 | A | 25 | 100% | 16.04s | $0.00775 | 9 | 56% |
| T4 | B | 25 | 100% | 1.59s | $0.00044 | - | 0% |
| T4 | C | 25 | 100% | 0.74s | $0.00018 | - | 0% |

## 2. The harness tradeoff: managed vs self-orchestrated (same model)

| Task | A cost | B cost | cost x | A latency | B latency | latency x | A pass% | B pass% |
|------|--------|--------|--------|-----------|-----------|-----------|---------|---------|
| T1 | $0.00486 | $0.00085 | 5.7x | 12.8s | 3.11s | 4.1x | 100% | 100% |
| T2 | $0.00414 | $0.00065 | 6.4x | 12.03s | 2.77s | 4.3x | 100% | 100% |
| T3 | $0.00318 | $0.00092 | 3.4x | 12.01s | 3.22s | 3.7x | 100% | 100% |

**Headline: the managed runtime costs ~5x more and runs ~4x slower than self-orchestrating the same model class, on these tasks.**

## 3. Portability: does one AGENTS.md cross runtimes? (T4)

One markdown control surface (format rule: `RESULT: <answer> | CONFIDENCE: <0-1>`, no markdown). Fed each runtime its native way.

| Arm | Runtime | N | Answer correct% | Format-compliant% | Both% |
|-----|---------|---|-----------------|-------------------|-------|
| A | Google Managed Agent (AGENTS.md inline) | 25 | 100% | 100% | 100% |
| B | Gemini direct (system prompt) | 25 | 100% | 100% | 100% |
| C | Claude (system prompt) | 25 | 100% | 100% | 100% |

## 4. Failure taxonomy

No failures recorded.

## 5. Totals

- Total executions: 225
- Total estimated cost: $0.5743
- Arm A median steps/run: 4.0
- Arm A runs that executed code in the sandbox: 61%

## 6. Soundbite stats (for the post)

- Same model, two harnesses: managed ~5x the cost, ~4x the wall-clock.
- One AGENTS.md, three runtimes, format-compliance: A 100%, B 100%, C 100%