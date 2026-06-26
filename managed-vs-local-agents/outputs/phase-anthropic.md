# Anthropic: managed vs single-call (claude-haiku-4-5)

Same T1-T3 battery. N=12/cell. Cost = token estimate (haiku $1/$5 per 1M + cache); managed hosted-compute overhead not in tokens, so managed cost is a floor.

| Task | Arm | N | Pass% | Median latency | Avg cost | % used tool |
|------|-----|---|-------|----------------|----------|-------------|
| T1 | managed | 12 | 100% | 6.69s | $0.00301 | 100% |
| T1 | single | 12 | 100% | 4.79s | $0.00600 | 100% |
| T2 | managed | 12 | 100% | 6.72s | $0.00297 | 100% |
| T2 | single | 12 | 100% | 3.95s | $0.00542 | 100% |
| T3 | managed | 12 | 100% | 4.55s | $0.00157 | 0% |
| T3 | single | 12 | 100% | 1.88s | $0.00424 | 100% |

## Managed vs single (Anthropic, same model)

| Task | managed $ | single $ | cost x | managed lat | single lat | lat x |
|------|-----------|----------|--------|-------------|------------|-------|
| T1 | $0.00301 | $0.00600 | 0.5x | 6.69s | 4.79s | 1.4x |
| T2 | $0.00297 | $0.00542 | 0.5x | 6.72s | 3.95s | 1.7x |
| T3 | $0.00157 | $0.00424 | 0.4x | 4.55s | 1.88s | 2.4x |

**Total estimated cost this run: $0.2785**