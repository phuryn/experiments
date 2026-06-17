# frontier-vs-open-audit — an open-weights model vs the closed frontier on a real code audit

**Question:** GLM-5.2 (Z.ai, MIT open weights) hit #2 on Code Arena, behind only Claude Fable 5 — the top open-weights model on the board. On a *real* codebase audit, how does it stack up against the closed frontier (Opus 4.8, GPT-5.5)?

**Method:** One real app (private; de-identified here). 21 bugs planted by hand across auth, RBAC, token/timing, logic & validation, invariants, performance, and UI. Three models audited the repo — each at **maximum reasoning effort**, single-agent, **read-only**, same prompt ([prompt.txt](prompt.txt)). **10 independent runs per model = 30 audits.** Each run's report was **blind-graded** against the planted-bug answer key: a run "catches" a bug only when its report names that specific defect. Trap seeds (decoys) were tracked separately to watch for false positives.

- Opus 4.8 and GLM-5.2 ran on the **Claude Code CLI** (`claude -p`). GLM-5.2 is driven through a ~120-line Anthropic-API shim ([harness/glm_claude_proxy.py](harness/glm_claude_proxy.py)) that rewrites the model slug to `z-ai/glm-5.2` and forwards to OpenRouter — so the open model drives the *real* harness, apples-to-apples with Opus.
- GPT-5.5 ran on the **OpenAI Codex CLI** ([harness/codex_audit.py](harness/codex_audit.py), `codex exec --json`, read-only sandbox).

**Results — planted-bug recall (10 runs each, 210 chances per model):**

| Model | Caught | Recall |
|---|---|---|
| Opus 4.8 | 50 / 210 | **24%** |
| GPT-5.5 | 39 / 210 | **19%** |
| GLM-5.2 (open) | 33 / 210 | **16%** |

Per-bug and per-category counts: [recall.csv](recall.csv). Full per-run grid: [matrix.json](matrix.json).

**Findings:**
1. **All three land around one in five.** Single-pass, max-effort audit recall is low across the board — none of these models is a thorough auditor on the first pass.
2. **The open model is in the frontier's range.** GLM-5.2 (free, self-hostable, MIT) trails the leader by 8 points and sits 3 behind GPT-5.5 — same band, not an outlier. The Code Arena ranking's *direction* holds on a real task.
3. **GLM led one category:** invariant / cross-check bugs — the kind where two files have to agree — 7/20 vs Opus 6, GPT-5.5 3.
4. **Recall is unstable run to run.** The same model on the same code returns a different bug list each run; that's why this is 10 runs per model, not one.

**Caveats:**
- One app, one audit task, n=10 per model. This is *planted-bug recall*, not a general code-quality score.
- The same audits also surfaced **real pre-existing bugs** in the app (none critical). Those are being fixed; a separate write-up will follow once they're closed.
- **De-identified.** Bug rows are category-level descriptors. The raw per-run reports and the seeded diffs quote the private repo and are **withheld** (same convention as the other sets here — the CSV/JSON are content-free). The answer key and seeded source are not published.
- GPT-5.5 ran on the Codex CLI, the Claude pair on the Claude Code CLI — different harnesses. This compares each model in a native agentic harness at max effort, not a single unified harness.
- Numbers are blind-graded. If a number here and a post disagree, the data here wins: [@PawelHuryn](https://x.com/PawelHuryn).

**Files:** `README.md`, `recall.csv`, `matrix.json`, `prompt.txt`, `harness/` (`glm_claude_proxy.py`, `codex_audit.py`, `build_matrix.py`, `grade_audits.js`). Inputs that quote the private repo (answer key, seeded diffs, raw reports) are withheld.

**Source post:** _(link added on publish)_
