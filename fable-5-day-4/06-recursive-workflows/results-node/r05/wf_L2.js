'use strict';
const { execFileSync } = require('child_process');

const dir = '<WORKDIR>/Temp/output/fable5-n10/recwf-node/r05';
const l3 = dir + '/wf_L3.js';

const prompt = `You are L2 in a recursion experiment. Follow these steps exactly:

Step 1: Write file: ${l3}
The file must be a Node.js script under 40 lines that:
- Runs TWO claude calls in PARALLEL using child_process.execFile with callbacks
- Model: claude-haiku-4-5-20251001  Flag: --allowedTools Bash
- Prompt for each: Reply in exactly one line. Format: L3 LEAF: then a 10-word tip for PMs using Claude Fable 5. No other output.
- Each execFile options: stdio ['ignore','pipe','pipe'], timeout 600000, encoding 'utf8'
- When both complete, print each as: L3 OK: <first line of that call's stdout>

Step 2: Run with Bash (timeout 600000): node ${l3}

Step 3: Your output must end with exactly this line: L2 OK: <first line of output from Step 2>`;

const out = execFileSync('claude', [
  '-p', prompt,
  '--model', 'claude-sonnet-4-6',
  '--allowedTools', 'Bash,Write',
  '--permission-mode', 'acceptEdits'
], { stdio: ['ignore', 'pipe', 'pipe'], timeout: 600000, encoding: 'utf8' });

process.stdout.write(out);
