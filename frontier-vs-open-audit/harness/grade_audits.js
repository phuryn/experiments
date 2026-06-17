export const meta = {
  name: 'grade-audit-repo-audits',
  description: 'Blind-judge each audit-repo audit against the tiered seeded + real-bug answer keys',
  phases: [
    { title: 'Enumerate', detail: 'list the audit report files' },
    { title: 'Judge', detail: 'one blind judge per audit report' },
  ],
}

// Self-contained: stable Temp paths hardcoded so it never depends on args passing through.
// The judge is told only "an audit report" — never which model produced it. Identity-blind by design.
const AUDIT_DIR  = './data\\audit_runs'
const ANSWER_KEY = './audit-repo\\answer_key.json'
const REAL_BUGS  = './audit-repo\\real_bugs.json'

const FILES = {
  type: 'object', additionalProperties: false, required: ['files'],
  properties: { files: { type: 'array', items: { type: 'string' },
    description: 'Bare filenames (e.g. "OPUS_r01.txt") of every audit report in the directory.' } },
}

const VERDICT = {
  type: 'object',
  additionalProperties: false,
  required: ['live_seeds_caught', 'superseded_flagged_as_live', 'superseded_caught_with_history',
             'real_bugs_caught', 'false_positive_count'],
  properties: {
    live_seeds_caught: {
      type: 'array', items: { type: 'string' },
      description: 'IDs of LIVE-tier seeded bugs this report genuinely identifies: names the right file AND the specific defect (the actual wrong behavior), not just "this area looks risky". Cross-file bugs must connect BOTH locations. Headline recall axis.',
    },
    superseded_flagged_as_live: {
      type: 'array', items: { type: 'string' },
      description: 'IDs of SUPERSEDED-tier seeds the report flags as a real/live bug WITHOUT noting a later migration overrides it — cries wolf on dead code. Precision/over-claim signal.',
    },
    superseded_caught_with_history: {
      type: 'array', items: { type: 'string' },
      description: 'IDs of SUPERSEDED-tier seeds where the report identifies the change AND correctly notes it is overridden / has no live effect (traced the migration history). The diligent catch.',
    },
    real_bugs_caught: {
      type: 'array', items: { type: 'string' },
      description: 'IDs from the real-bug key this report genuinely identifies.',
    },
    false_positive_count: {
      type: 'integer',
      description: 'Count of claimed issues that are NEITHER a seeded bug (any tier) NOR a plausible genuine defect — wrong/hallucinated. Do NOT count superseded-flagged-as-live here.',
    },
    fp_examples: { type: 'array', items: { type: 'string' }, description: 'Up to 3 short quotes of false-positive claims.' },
    notes: { type: 'string' },
  },
}

phase('Enumerate')
const listing = await agent(
  `List every audit report file in this directory: ${AUDIT_DIR}\n` +
  `Return the bare filenames (not full paths) of all files matching the pattern <LABEL>_r<NN>.txt ` +
  `(e.g. OPUS_r01.txt, GLM_r12.txt, CODEX_r03.txt). Do NOT include summary_*.csv, MANIFEST.md, grades_*.json or any other file.`,
  { label: 'enumerate-reports', phase: 'Enumerate', schema: FILES, agentType: 'Explore' }
)
// Equal N per model: grade exactly r01–r10 for each (the tile grid needs rectangular cells).
const files = (listing?.files || []).filter(f => /^(OPUS|GLM|CODEX)_r(0[1-9]|10)\.txt$/i.test(f))
const audits = files.map(f => ({ file: `${AUDIT_DIR}\\${f}`, runId: f.replace(/\.txt$/i, '') }))
log(`grading ${audits.length} audits (tiered), blind to model identity`)

phase('Judge')
const results = await parallel(audits.map(a => () =>
  agent(
    `You are grading ONE pre-release code-audit report against two answer keys. Be strict and objective.\n\n` +
    `1. Read the seeded-bug answer key: ${ANSWER_KEY}\n` +
    `   Each seed has a "tier" field: "live" (in code that executes) or "superseded" (a change in an early\n` +
    `   SQL migration that a LATER migration overrides, so it has NO effect on the live schema).\n` +
    `2. Read the real-bug answer key: ${REAL_BUGS}\n` +
    `3. Read the audit report under test: ${a.file}\n\n` +
    `SCORING:\n` +
    `- live_seeds_caught: LIVE-tier seeds the report genuinely identifies (correct file AND the specific\n` +
    `  defect/wrong behavior; cross-file seeds must connect both locations). Not merely "this looks risky".\n` +
    `- For SUPERSEDED-tier seeds, decide per seed:\n` +
    `    * superseded_caught_with_history: identifies the change AND notes it is overridden by a later\n` +
    `      migration / has no live effect (traced the history).\n` +
    `    * superseded_flagged_as_live: flags it as a real/live bug WITHOUT noting it is overridden (cries wolf).\n` +
    `    * if not mentioned at all, put it in neither list.\n` +
    `- real_bugs_caught: IDs from the real-bug key genuinely identified.\n` +
    `- false_positive_count: claimed issues that are neither any seeded bug nor a plausible genuine defect\n` +
    `  (hallucinated/wrong). Do NOT count superseded-flagged-as-live here. Do NOT penalize a genuine defect\n` +
    `  simply missing from both keys — only clearly wrong claims.\n\n` +
    `Return the structured verdict. The report is anonymous; judge only its content.`,
    { label: `judge:${a.runId}`, phase: 'Judge', schema: VERDICT, agentType: 'Explore' }
  ).then(v => ({ runId: a.runId, ...v })).catch(() => ({ runId: a.runId, error: true }))
))

return results
