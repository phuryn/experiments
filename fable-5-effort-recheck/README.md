# Fable 5: Effort-Dial Recheck (Restored Build, July 3, 2026)

**Question:** on the restored July-3 build, what does `--effort` actually buy — in wall-clock time *and* output tokens — on normal work versus genuinely hard work, for Claude Fable 5 and Opus 4.8?

**Short answer:** on normal work the dial is a *cost* lever, not a *quality* lever — every graded normal-work answer is correct at every level, and turning the dial up buys ~2–3x the time and ~4–5x the tokens for the same verdict. Quality only moves on genuinely hard work, and only for Fable: catch-rate on a planted cross-file contradiction stays at zero through `high`, then crosses a threshold at `xhigh` (2/5) and `max` (3/5). Opus never catches it at any level (0/25). And Fable writes *fewer* output tokens than Opus at every level while doing so.

## Setup

- **Harness:** `claude -p`, subscription surface, `--output-format json` (exact output/input token counts from the CLI's own `usage`; thinking is folded into `output_tokens`, no separate reasoning-token field is exposed). Write/search tools denied on every run. Wall-clock includes CLI startup. Build: **Claude Code CLI 2.1.198, 2026-07-03** (day-4 reference build was 2.1.173, June 12).
- **Effort is explicit, never default.** This box had `CLAUDE_EFFORT=xhigh` in the environment and `effortLevel: xhigh` persisted in settings; the environment var is stripped from the child and **every run passes an explicit `--effort` flag**, so no cell inherits a hidden level. Design mirrors day-4 `run_set01.py`: matched lanes, fixed-seed shuffle, round-robin deal, lane stagger, outliers kept, failed runs stay in the CSV with their `rc`.
- **Base grid (`run_grid.py`, n=8/cell, 160 runs):** three task tiers run on Fable — **easy** (explain in exactly 3 bullets), **realistic** (a two-file contradiction check against a private content repo), **audit** (a planted-contradictions doc audit graded 0–3 against regexes written before any run, in `expected.json`) — plus an **Opus realistic control** (`--model claude-opus-4-8`). Every tier × every level `low|medium|high|xhigh|max`.
- **Needle tier (`run_needle.py`, FLAT n=5/cell, 50 runs):** the proven planted cross-file contradiction from the day-4 / `frontier-vs-open-audit` lineage — same verbatim prompt, same strict/loose grading (`needle_expected.json`). One planted bug: a one-liner follower-ceiling clash across three craft files (`<50K` gate in one file vs `~75K` ceiling in another). **n=5 per cell, flat, no adaptive extensions** — Pawel's call (a +2 top-up was reserved and not spent). Strict = both sides named; loose = either keyword. Both models × all five levels.
- **Off-domain probe (`probe_skill.py`, n=1):** one-shot Opus at `xhigh` with a security-audit method preamble prepended to the same needle task — an anecdote arm, labeled `needle-skill`, not pooled with anything.
- **Totals:** 160 grid + 50 needle = **210 graded runs**, plus the 1 off-domain probe. 212 rows logged, 211 clean, 1 failed (one `max` needle run timed out at the 900s ceiling, `rc=-9`; re-run to hold n=5 clean — the failed row is kept in `runs.csv`).

## Results

### 1. Normal work — the dial costs time and tokens, buys nothing else

Medians per `--effort` level (`low / medium / high / xhigh / max`):

| Tier (model) | Time (s) | Output tokens | Quality |
|---|---|---|---|
| **realistic (Fable)** | 24.6 / 25.4 / 29.3 / 35.0 / **54.3** | 750 / 901 / 1099 / 1512 / **2,936** | ungraded (day-4 parity) |
| **realistic (Opus, control)** | 25.1 / 29.3 / 27.6 / 42.8 / **72.4** | 1,057 / 1,358 / 1,342 / 2,407 / **5,102** | ungraded |
| **easy (Fable)** | 13.7 / 15.0 / 16.8 / 20.0 / **31.6** | 318 / 374 / 407 / 702 / **1,544** | exactly-3-bullets **8/8 every level** |
| **audit (Fable)** | 20.8 / 22.2 / 25.8 / 27.0 / **33.9** | 490 / 710 / 911 / 1,143 / **1,902** | planted-bugs **3/3 every level** |

`low → max` costs ~2.2x time / 3.9x tokens (Fable realistic), ~2.9x / 4.8x (Opus realistic), ~2.3x / 4.9x (Fable easy). Quality is flat: every easy answer keeps exactly 3 bullets, every audit run catches all 3 planted contradictions, at every level. **Fable writes fewer output tokens than Opus at every single realistic level** (750 vs 1,057 at low … 2,936 vs 5,102 at max).

### 2. Hard work — the cliff (needle, strict catch, n=5/cell)

| Model | low | medium | high | xhigh | max |
|---|---|---|---|---|---|
| **Fable** | 0/5 | 0/5 | 0/5 | **2/5** | **3/5** |
| **Opus** | 0/5 | 0/5 | 0/5 | 0/5 | 0/5 |

Loose catch equals strict for Fable (every keyword hit was a genuine both-sides pairing); Opus is 0/5 loose at every level too (**0/25** either way). `high` catches nothing `medium` didn't — the extra cost is pure. The dial only starts paying on the needle at `xhigh`, and only for Fable.

Needle cost medians (`low / medium / high / xhigh / max`):

| Model | Time (s) | Output tokens |
|---|---|---|
| **Fable** | 117 / 161 / 251 / 384 / **593** | 7,906 / 11,916 / 19,479 / 29,302 / **45,145** |
| **Opus** | 132 / 171 / 205 / 323 / **441** | 9,170 / 12,387 / 14,675 / 24,376 / **33,521** |

Fable's `max` needle runs ran 563–681s (median 593; worst clean run 681s, plus the one 900s timeout). Opus is *faster* and writes *fewer* tokens on the needle at every level — and still catches it zero times. Fable's extra minutes and ~45K tokens at `xhigh`+ are what buy the catches.

**Off-domain probe (`needle-skill`, Opus + audit-method preamble, `xhigh`, n=1):** 380s, 28,765 tokens, **strict 0/1, loose 0/1** — one-shot, missed the needle. A single anecdote, not a rate.

## Findings

1. **Normal work is level-invariant in quality.** Easy and audit tiers are saturated (8/8 bullets, 3/3 bugs) at every level; realistic answers land the same verdict. Turning the dial up on normal work only spends time (~2–3x) and tokens (~4–5x).
2. **Hard work has a threshold, and it's at `xhigh`.** The planted needle stays at 0 catches through `high`, then Fable crosses to 2/5 (`xhigh`) and 3/5 (`max`). `high` is strictly worse value than `medium` here — more cost, zero extra catches.
3. **The threshold is Fable-only on this build.** Opus never catches the needle (0/25) despite the same dial, the same prompt, and *less* time/tokens spent — this is a recall gap the effort lever does not close for Opus.
4. **Fable is the leaner writer.** Fewer output tokens than Opus at every level, on both normal and hard work — so "higher effort" is not simply "more verbose."

## Method notes & caveats

- **n=5 needle cells — raw counts, no percentages.** With five runs a cell, "2/5" and "3/5" are reported as-is; do not read them as 40%/60% point estimates. FLAT n=5 was a deliberate design call, not a stopping-on-signal artifact.
- **One planted bug.** The needle is a *single* cross-file contradiction. It measures recall on that one bug, not general audit skill. The strict grader is a mechanical both-sides proxy (`50K` AND `75K|one-liner ceiling`); loose is either keyword.
- **The audit tier saturated — that's a hardness lesson, kept in the data.** The first invented-bugs audit tier (3 planted contradictions in two synthetic docs) came out 3/3 at *every* level for Fable. It does not discriminate effort, so it lives in the data as the `audit` task and as evidence that "an audit task" is not automatically hard — the needle had to be a specifically nasty, historically-proven bug to separate the levels.
- **Build drift vs the day-4 baseline.** On the same needle, day-4's *configured*-xhigh collection gave Fable 20/30 (67%) and Opus 2/30 (7%); today's *explicit*-xhigh cells give Fable 2/5 and Opus 0/5. These are different collections on drifting builds at small n — read the direction (Fable > Opus, dial helps Fable at the top), not the exact rate. The distractor content around the needle has also drifted since June; the needle line itself was re-verified present verbatim on 2026-07-03 (`needle_expected.json`).
- **Wall-clock includes CLI startup**; subscription surface, single machine, single build (2.1.198) — expect drift on later builds, exactly as day-4 warned.
- **Anonymization (full disclosure):** the published copy replaces the local checkout path with `<WORKDIR>` via the repo's checked-in rules ([.claude/hooks/](../.claude/hooks/)); nothing else is edited — every number, timestamp, verdict, and model-written line is as produced. Verified: zero occurrences of the private path components in this folder.
- **What's excluded / included.** Following the day-4 precedent, the raw `answers/` transcripts (213 model answer bodies — they quote a private content repo) are **not** published; the content-free `runs.csv`, harnesses, graders, expected-defs, and progress log are. The **needle's three audited files live in a private content repo and are referenced by path only, not copied.** The two synthetic **audit-tier** fixtures (`audit/*.md`) *are* included — they are purpose-built fictional infra docs with no private content, so the audit tier stays reproducible. Prompt paths in the scripts are quoted verbatim as run (they point at the working checkout under `<WORKDIR>`); a reproducer places the fixtures accordingly.

## Files

- `run_grid.py` — base grid harness (3 Fable tiers + Opus realistic control, n=8/cell).
- `run_needle.py` — needle harness (flat n=5/cell, both models).
- `probe_skill.py` + `needle_skill_prompt.txt` — the one-shot off-domain probe and its prompt.
- `analyze.py` — aggregates `runs.csv` → `summary.json` + the medians tables above.
- `expected.json` — the audit-tier planted contradictions + regex grader (written before any run).
- `needle_expected.json` — the needle reconstruction, verbatim prompt, grading scheme, and day-4 baselines.
- `runs.csv` — every run, one row each (212 rows; `correct_or_score` = strict, `loose_score` = final column).
- `summary.json` — per-cell medians and catch counts.
- `progress.log` — raw run-by-run progress.
- `audit/service-overview.md`, `audit/deploy-runbook.md` — the synthetic audit-tier fixtures.

## License

MIT. Use anything here however you like; a link back is appreciated.
