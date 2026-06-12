const { execFileSync } = require('child_process');

const base = '<WORKDIR>/Temp/output/fable5-n10/recwf-node/r09';
const wf3 = base + '/wf_L3.js';

const prompt = `You are workflow level L2. Use your Write and Bash tools to complete these steps IN ORDER:

STEP 1: Write a Node.js script to ${wf3} (under 40 lines) that:
- Uses worker_threads to run TWO parallel claude CLI calls
- In worker mode (isMainThread===false): call execFileSync from child_process with args:
  ['claude', ['-p', 'Output exactly one line in this format: L3 LEAF: <10-word tip for PMs using Claude Fable 5>', '--model', 'claude-haiku-4-5-20251001', '--allowedTools', 'Bash'], {stdio:['ignore','pipe','pipe'], timeout:600000, encoding:'utf8'}]
  Then do parentPort.postMessage(result.trim().split('\\n')[0])
  Wrap in try/catch; on error: parentPort.postMessage('L3 LEAF: error ' + e.message.slice(0,40))
- In main thread (isMainThread===true): create 2 workers using new Worker(__filename)
  Collect messages; when both arrive, print each as: console.log('L3 OK: ' + msg)

STEP 2: Run this exact command with your Bash tool: node ${wf3}
Wait for completion (may take 2 minutes).

STEP 3: Your FINAL output must be ONLY this one line — no other text:
L2 OK: <paste the first line printed by node here>`;

const out = execFileSync('claude', [
  '-p', prompt,
  '--model', 'claude-sonnet-4-6',
  '--allowedTools', 'Bash,Write',
  '--permission-mode', 'acceptEdits'
], { stdio: ['ignore', 'pipe', 'pipe'], timeout: 600000, encoding: 'utf8' });

process.stdout.write(out);
