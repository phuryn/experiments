// Set 06 nested arm: 1 sonnet manager writes+runs its own harness over 4 haiku leaves, then synthesizes itself.
// Usage: node nested.js <out-dir>
const { REPO, MONTHS, leafPrompt, runClaude, fs } = require('./lib');
const DIR = process.argv[2];
if (!DIR) { console.error('usage: node nested.js <out-dir>'); process.exit(1); }
fs.mkdirSync(`${DIR}/receipts`, { recursive: true });
for (const m of MONTHS) fs.writeFileSync(`${DIR}/leaf_prompt_${m}.txt`, leafPrompt(m));

const managerPrompt = `You are a workflow orchestrator running a real analysis pipeline. Work from ${REPO}.

Goal: produce a cross-month hook-pattern performance report at ${DIR}/final-report.md.

Steps:
1. Write a Node.js harness at ${DIR}/inner.js that spawns FOUR \`claude\` agents IN PARALLEL with child_process.spawn (argument arrays, never shell strings), one per month: 202603, 202604, 202605, 202606. For each month m, the -p argument is EXACTLY the contents of ${DIR}/leaf_prompt_<m>.txt (read the file in the harness and pass its contents as the -p argument). Flags per agent: --model haiku --output-format json --allowedTools Read --max-turns 8. Spawn with stdin ignored ('ignore'), 360000ms timeout, cwd ${REPO}. Collect each agent's JSON stdout; save the full JSON to ${DIR}/receipts/leaf_<m>.json and its .result field to ${DIR}/leaf_<m>.md.
2. Run the harness with Bash: node ${DIR}/inner.js
3. Read the four leaf_*.md analyses and synthesize the final report YOURSELF — do not spawn another agent for synthesis. Write ${DIR}/final-report.md (~500 words): 1) **Durable patterns** recurring across 2+ months, with months and numbers; 2) **Three actionable recommendations** for Pawel's next 10 posts, each tied to evidence; 3) **Two hypotheses worth testing**, each with supporting numbers.

Hard budget: exactly 4 claude calls total, all spawned by the harness. No retries unless a leaf returns malformed JSON. When done, reply with one line: DONE.`;

(async () => {
  const t0 = Date.now();
  const mgr = await runClaude({ prompt: managerPrompt, model: 'sonnet', allowedTools: 'Bash,Write,Read', maxTurns: 40, timeoutMs: 1200000, label: 'manager' });
  const wall = (Date.now() - t0) / 1000;
  const leafReceipts = MONTHS.map((m) => {
    const j = JSON.parse(fs.readFileSync(`${DIR}/receipts/leaf_${m}.json`, 'utf8'));
    return { label: `leaf_${m}`, wall: j.duration_ms / 1000, cost: j.total_cost_usd, turns: j.num_turns, usage: j.usage };
  });
  const { result, ...mgrR } = mgr;
  const receipts = [mgrR, ...leafReceipts];
  const total = receipts.reduce((s, r) => s + r.cost, 0);
  fs.writeFileSync(`${DIR}/receipts.json`, JSON.stringify({ arm: 'nested', wall, total, receipts }, null, 2));
  console.log(JSON.stringify({ arm: 'nested', wall, total }));
})().catch((e) => { console.error(e.message); process.exit(1); });
