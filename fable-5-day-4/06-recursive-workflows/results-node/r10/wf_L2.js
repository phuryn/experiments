'use strict';
const { execFileSync } = require('child_process');
const d = '<WORKDIR>/Temp/output/fable5-n10/recwf-node/r10';
const l3src = [
  "const {execFile}=require('child_process');",
  "const run=()=>new Promise((res,rej)=>execFile('claude',['-p','Output exactly one line: L3 LEAF: <10-word tip for PMs using Claude Fable 5>','--model','claude-haiku-4-5-20251001','--allowedTools','Bash'],{timeout:600000,stdio:['ignore','pipe','pipe']},(e,o)=>e?rej(e):res(o.trim().split('\\n').find(l=>l.startsWith('L3 LEAF:'))||o.trim().split('\\n')[0])));",
  "Promise.all([run(),run()]).then(([a,b])=>{console.log('L3 OK: '+a);console.log('L3 OK: '+b)}).catch(e=>{console.error(e.message);process.exit(1)});"
].join('\n');
const prompt =
  'You are workflow level L2. Complete these tasks in order:\n\n' +
  'TASK 1: Use the Write tool to create the file ' + d + '/wf_L3.js\n' +
  'Write EXACTLY these 3 lines as the file content (no modifications, no extra lines):\n' +
  l3src + '\n\n' +
  'TASK 2: Use the Bash tool to run: node ' + d + '/wf_L3.js\n' +
  'Wait for it to finish.\n\n' +
  'TASK 3: Your final text output must be EXACTLY this one line:\n' +
  'L2 OK: <replace with the first line of the node command stdout>\n' +
  'No other text — no preamble, no explanation.';
try {
  const buf = execFileSync('claude', [
    '-p', prompt, '--model', 'claude-sonnet-4-6',
    '--allowedTools', 'Bash,Write', '--permission-mode', 'acceptEdits'
  ], { timeout: 600000, stdio: ['ignore', 'pipe', 'pipe'] });
  const lines = buf.toString().trim().split('\n');
  const l2 = lines.find(l => l.startsWith('L2 OK:')) || lines[lines.length - 1];
  console.log(l2);
} catch (e) {
  console.error('L2 ERR:', (e.stdout || Buffer.alloc(0)).toString().slice(0, 800) || e.message);
  process.exit(1);
}
