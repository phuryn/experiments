// Recursive dynamic workflow test, L1 seed (set 05 variant B, per-run dir baked in).
// Each level's orchestrator for the NEXT level is written by the model at this level.
const { execFileSync } = require('child_process');
const DIR = '<WORKDIR>/Temp/output/fable5-n10/recwf-node/r06';
const t0 = Date.now();
const prompt = `You are workflow level L1 of a recursion experiment. Working dir: ${DIR}.
Your job:
1. Write ${DIR}/wf_L2.js: a Node script that calls "claude -p" (model sonnet, flags: --allowedTools "Bash,Write" --permission-mode acceptEdits) with instructions to act as level L2: L2 must write ${DIR}/wf_L3.js (same pattern, level L3) and run it with node, then print "L2 OK: " plus the first line of L3's output.
2. wf_L3.js is the FLOOR: instead of writing a child, its claude call (model haiku, --allowedTools Bash) must answer in one line: "L3 LEAF: <a 10-word tip for PMs using Claude Fable 5>". wf_L3.js runs TWO such haiku calls in parallel and prints both lines prefixed "L3 OK:".
3. After writing wf_L2.js, run: node ${DIR}/wf_L2.js  and print its full output prefixed "L1 SAW: ".
4. Final line of your output: "L1 OK".
Keep every generated script under 40 lines. Use execFileSync with argument arrays (no shell command strings) and 600000ms timeout. IMPORTANT: every claude spawn in generated scripts must ignore stdin (stdio: ['ignore','pipe','pipe']) or claude hangs waiting for input. When you run node wf_L2.js with your Bash tool, pass timeout 580000 (the inner chain takes minutes; the default 2-minute Bash timeout will kill it).`;
try {
  const out = execFileSync('claude',
    ['-p', prompt, '--model', 'sonnet', '--allowedTools', 'Bash,Write', '--permission-mode', 'acceptEdits'],
    { encoding: 'utf8', timeout: 1200000, stdio: ['ignore', 'pipe', 'pipe'] });
  console.log(out);
} catch (e) {
  console.log('L1 FAILED:', e.message, (e.stdout || '').slice(-2000));
}
console.log(`WALL: ${((Date.now() - t0) / 1000).toFixed(1)}s`);
