# silicon-gambit-chess — The Silicon Gambit (LLM chess benchmark)

> **The code and live app live in their own repo:** [github.com/phuryn/lll-chess-leaderboard](https://github.com/phuryn/lll-chess-leaderboard) ↗
> **Live board + leaderboard:** [chess.productcompass.pm](https://chess.productcompass.pm/) ↗
>
> This folder is a pointer so the experiment shows up in the repo's folder list. It is not a fork — nothing here is maintained separately.

**Question:** Can frontier LLMs actually *play* chess — not solve a puzzle, but hold a legal, stateful game to the end — and how do they rank against each other head to head?

**Method:** Models play full games through an n8n-orchestrated chess API, submitting moves in Standard Algebraic Notation (SAN). A stateful [chess.js](https://github.com/jhlywa/chess.js) engine validates every move against the live board: **an illegal move is an instant loss** — no retries, no hand-holding. Games and results persist in Supabase; a points leaderboard ranks the field. The whole harness (n8n flows, API, engine wiring, persistence, the live board) is in the [linked repo](https://github.com/phuryn/lll-chess-leaderboard).

**Why it's here:** it's part of the same body of firsthand model experiments as the other sets in this repo — the receipt behind the chess-benchmark posts. Because it's a hosted, stateful app rather than a one-shot script, it stays in its own repo; this stub keeps it visible alongside the folder-based experiments.

**Ran:** Dec 2025 – Feb 2026.
