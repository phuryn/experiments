# silicon-gambit-chess — The Silicon Gambit (LLM chess benchmark)

> **The code and live app live in their own repo:** [github.com/phuryn/lll-chess-leaderboard](https://github.com/phuryn/lll-chess-leaderboard) ↗
> **Live board + current standings:** [chess.productcompass.pm](https://chess.productcompass.pm/) ↗
>
> This folder is a pointer so the experiment shows up in the repo's folder list. It is not a fork — the standings below are a snapshot; the live board is the source of truth.

**Question:** Can frontier LLMs actually *play* chess — not solve a puzzle, but hold a legal, stateful game to the end — and how do they rank head to head?

**Method:** Models play full games through an n8n-orchestrated chess API, submitting moves in Standard Algebraic Notation (SAN). A stateful [chess.js](https://github.com/jhlywa/chess.js) engine validates every move against the live board and detects checkmate, stalemate, and draws. Games persist in Supabase (PostgreSQL). Two modes: **FEN** (the model receives the exact board position each turn) and **blindfold** (the model must reconstruct the board from move history alone). The full harness — n8n flows, API, engine, persistence, live board — is in the [linked repo](https://github.com/phuryn/lll-chess-leaderboard).

**Scoring:** win +1, draw +0.5, loss -1. **An illegal move is an instant loss** — no retries. Adherence to the format is part of the test.

## Standings (snapshot — see the [live board](https://chess.productcompass.pm/) for current)

### Experiment 1 — The Vision Test (FEN, board given each turn)

| Rank | Model | Wins | Losses | Invalid moves | Score |
|---|---|---|---|---|---|
| 1 | gpt-5.2 | 34 | 1 | 0 | +33.5 |
| 2 | gpt-5.1 | 28 | 7 | 6 | +21.5 |
| 3 | gemini-3 | 24 | 12 | 12 | +12 |
| 4 | claude-opus-4.5 | 15 | 21 | 21 | -6 |
| 5 | gpt-4.1-mini | 14 | 22 | 22 | -8 |
| 6 | deepseek-v3.2 | 9 | 27 | 27 | -18 |
| 7 | kimi-k2 | 1 | 35 | 35 | -34 |

### Experiment 2 — Blindfold (history only, no board given)

| Rank | Model | Wins | Losses | Invalid moves | Score |
|---|---|---|---|---|---|
| 1 | gpt-5.1 | 32 | 4 | 3 | +28 |
| 2 | gemini-3 | 29 | 7 | 7 | +22 |
| 3 | gpt-5.2 | 28 | 8 | 7 | +20 |
| 4 | gpt-4.1-mini | 17 | 19 | 19 | -2 |
| 5 | claude-opus-4.5 | 14 | 22 | 22 | -8 |
| 6 | kimi-k2 | 6 | 30 | 30 | -24 |
| 7 | deepseek-v3.2 | 0 | 36 | 36 | -36 |

## Findings

1. **Output discipline is the real test.** Kimi-k2 and DeepSeek-V3.2 collapsed not on chess strength but on constraint-following: apologizing mid-game, inventing board states, mixing reasoning into the move output. Every one of those is an instant loss. The models that top the board are the ones that stay in format across many turns — the same trait that separates production-ready agents.
2. **Catastrophic forgetting past ~30 moves (blindfold).** With only move history to go on, models lose track of the board as the game gets long and start playing illegal moves. A scratchpad tool for the blindfolded models mitigates it.
3. **The blindfold paradox did not hold.** Early runs hinted weaker models survived longer blindfold than with the board given; more testing made the effect inconsistent, so it is not a claim.

**Tech:** React, TypeScript, Vite, Tailwind, shadcn/ui, Supabase (PostgreSQL), chess.js, n8n.

**Ran:** Dec 2025 – Feb 2026.
