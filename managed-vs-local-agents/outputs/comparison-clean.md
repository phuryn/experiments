# CLEAN comparison: managed loop vs true local loop

Same T1-T3 tasks. N=6/cell. MANAGED = provider runs the loop in its sandbox. LOCAL = I run the loop here (base API per step + local Python execution, free CPU). Cost = token estimate at tier rates (+ OpenAI code_interpreter $0.03/container; Anthropic-managed cache pricing). Caching reported as-used: managed auto-caches its large agent context; local context is lean.

| Provider | Arm | N | Pass% | Median latency | Avg cost | % tool |
|---|---|---|---|---|---|---|
| anthropic | local | 18 | 100% | 2.12s | $0.00221 | 100% |
| anthropic | managed | 18 | 100% | 5.99s | $0.00255 | 67% |
| google | local | 18 | 100% | 2.88s | $0.00077 | 100% |
| google | managed | 18 | 100% | 12.3s | $0.00403 | 67% |
| openai | local | 18 | 100% | 5.78s | $0.00065 | 100% |
| openai | managed | 18 | 100% | 6.69s | $0.01060 | 33% |

## Managed vs local (per provider)

| Provider | managed $ | local $ | cost x | managed lat | local lat | lat x |
|---|---|---|---|---|---|---|
| anthropic | $0.00255 | $0.00221 | 1.2x | 5.99s | 2.12s | 2.8x |
| google | $0.00403 | $0.00077 | 5.3x | 12.3s | 2.88s | 4.3x |
| openai | $0.01060 | $0.00065 | 16.4x | 6.69s | 5.78s | 1.2x |

**Total estimated cost: $0.3745**

## The average is misleading — read it per task

The OpenAI "16.4x" above is one code-firing task dragging up two near-free ones. Broken out by task (managed/local cost ratio + whether the agent actually ran code):

| Task | runs code? | Google | Anthropic | OpenAI |
|---|---|---|---|---|
| T1 prime-sum | yes (all 3) | 7.0x | 1.3x | **~65x** ($0.0306 vs $0.0005) |
| T2 mean-of-squares | Google yes; OpenAI/Anthropic no | 8.0x | 1.6x | **~1.0x** |
| T3 bat&ball (pure reasoning) | none | **2.9x** | 0.7x | **~0.6x** (cheaper) |

## "Managed" is three different pricing bets

- **Google = sandbox tax.** ~5x on average, and still **2.9x on T3 where no code runs at all.** You rent an always-on sandbox; you pay whether or not the agent executes anything.
- **Anthropic = ~no tax.** ~1.2x, *cheaper* than local on T3. Auto-caching of the agent context absorbs the managed overhead.
- **OpenAI = code tax.** == local (sometimes cheaper) on reasoning tasks; +$0.03 flat container fee only when `code_interpreter` fires. Not a runtime tax. A per-code-execution tool fee.

The model decides whether to run code: gpt-5-mini solved T2/T3 in reasoning (no container, no fee) and fired the container only on T1. So OpenAI's managed cost is workload-dependent, not fixed.

(OpenAI arm = the real hosted Agent Builder workflow `wf_68f0aace...` via `POST /v1/workflows/{id}/run`, streamed for usage/output. See FINDINGS §K-v2 / §L.)