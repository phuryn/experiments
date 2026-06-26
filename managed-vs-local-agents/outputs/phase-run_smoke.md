# Run summary: smoke

Tasks: ['T1', 'T2', 'T3', 'T4'] | Arms: ['A', 'B', 'C'] | N per cell: 1 | total runs: 9
_Cost is an ESTIMATE from token counts (gemini in/out $0.30/$2.50, claude $1/$5 per 1M). Treat as directional._

| Task | Arm | N | Pass | Pass% | med latency | avg cost | top failure |
|------|-----|---|------|-------|-------------|----------|-------------|
| T1 | A | 1 | 1 | 100% | 15.62s | $0.00487 | - |
| T1 | B | 1 | 1 | 100% | 2.27s | $0.00045 | - |
| T2 | A | 1 | 1 | 100% | 12.91s | $0.00346 | - |
| T2 | B | 1 | 1 | 100% | 3.09s | $0.00067 | - |
| T3 | A | 1 | 1 | 100% | 12.1s | $0.00321 | - |
| T3 | B | 1 | 1 | 100% | 9.06s | $0.00075 | - |
| T4 | A | 1 | 1 | 100% | 16.01s | $0.00794 | - |
| T4 | B | 1 | 1 | 100% | 2.05s | $0.00071 | - |
| T4 | C | 1 | 1 | 100% | 0.73s | $0.00018 | - |

## Failure taxonomy (all cells)


**Total estimated cost this run: $0.0222**