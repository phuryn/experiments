const { execFileSync } = require('child_process');
const fs = require('fs');
const dir = '<WORKDIR>\\Temp\\output\\fable5-n10\\recwf-node\\r04';
const l3path = dir + '\\wf_L3.js';

// L2 writes wf_L3.js
const l3src = `const { execFileSync } = require('child_process');
const { Worker, isMainThread, parentPort } = require('worker_threads');
if (!isMainThread) {
  const r = execFileSync('claude', ['-p', 'Reply with exactly one line: L3 LEAF: <a 10-word tip for PMs using Claude Fable 5>', '--model', 'claude-haiku-4-5-20251001', '--allowedTools', 'Bash'], { stdio: ['ignore','pipe','pipe'], timeout: 120000 });
  parentPort.postMessage(r.toString().trim().split('\\\\n').find(l => l.startsWith('L3 LEAF:')) || r.toString().trim().split('\\\\n')[0]);
} else {
  const mk = () => new Promise((res, rej) => { const w = new Worker(__filename); w.on('message', res); w.on('error', rej); });
  Promise.all([mk(), mk()]).then(([a, b]) => { console.log('L3 OK: ' + a); console.log('L3 OK: ' + b); }).catch(e => { console.error(e); process.exit(1); });
}
`;
fs.writeFileSync(l3path, l3src);

// L2 calls claude to run wf_L3.js and capture output
const prompt = 'Run this command and return ONLY the first line of its stdout, prefixed with "L2 OK: ":\nnode ' + l3path + '\nDo not add any other text.';

const out = execFileSync('claude', [
  '-p', prompt,
  '--model', 'claude-sonnet-4-6',
  '--allowedTools', 'Bash',
  '--permission-mode', 'acceptEdits'
], { stdio: ['ignore','pipe','pipe'], timeout: 540000 });

const lines = out.toString().trim().split('\n');
const hit = lines.find(l => l.startsWith('L2 OK:')) || ('L2 OK: ' + lines[0]);
console.log(hit);
