// Set 06 flat arm: L0 harness (this file, 0 tokens) -> 4 haiku leaves in parallel -> 1 sonnet synthesis.
// Usage: node flat.js <out-dir>
const { MONTHS, leafPrompt, synthPrompt, runClaude, fs } = require('./lib');
const DIR = process.argv[2];
if (!DIR) { console.error('usage: node flat.js <out-dir>'); process.exit(1); }
fs.mkdirSync(DIR, { recursive: true });

(async () => {
  const t0 = Date.now();
  const leaves = await Promise.all(MONTHS.map((m) =>
    runClaude({ prompt: leafPrompt(m), model: 'haiku', allowedTools: 'Read', maxTurns: 8, timeoutMs: 360000, label: `leaf_${m}` })
  ));
  for (const l of leaves) fs.writeFileSync(`${DIR}/${l.label}.md`, l.result);
  const synth = await runClaude({ prompt: synthPrompt(DIR), model: 'sonnet', allowedTools: 'Read', maxTurns: 10, timeoutMs: 360000, label: 'synthesis' });
  fs.writeFileSync(`${DIR}/final-report.md`, synth.result);
  const wall = (Date.now() - t0) / 1000;
  const receipts = [...leaves, synth].map(({ result, ...r }) => r);
  const total = receipts.reduce((s, r) => s + r.cost, 0);
  fs.writeFileSync(`${DIR}/receipts.json`, JSON.stringify({ arm: 'flat', wall, total, receipts }, null, 2));
  console.log(JSON.stringify({ arm: 'flat', wall, total }));
})().catch((e) => { console.error(e.message); process.exit(1); });
