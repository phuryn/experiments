# OpenAI: Responses+code_interpreter vs single (gpt-5-mini)

Same T1-T3 battery. N=12/cell. Cost = token estimate (gpt-5-mini ~$0.25/$2.00 per 1M) + ~$0.03 code_interpreter container surcharge when used.

| Task | Arm | N | Pass% | Median latency | Avg cost | % used code_interpreter |
|------|-----|---|-------|----------------|----------|-------------------------|
| T1 | hosted | 12 | 100% | 17.3s | $0.03058 | 100% |
| T1 | single | 12 | 100% | 35.32s | $0.00493 | 0% |
| T2 | hosted | 12 | 100% | 3.63s | $0.00067 | 0% |
| T2 | single | 12 | 100% | 4.12s | $0.00065 | 0% |
| T3 | hosted | 12 | 100% | 2.92s | $0.00044 | 0% |
| T3 | single | 12 | 100% | 2.39s | $0.00030 | 0% |

**Total estimated cost this run: $0.4508**