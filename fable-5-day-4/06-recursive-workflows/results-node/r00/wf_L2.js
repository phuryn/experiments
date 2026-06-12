const { execFileSync } = require('child_process');
const DIR = '<WORKDIR>/Temp/output/fable5-n10/recwf-node/r00';

const l3 = `const { execFile } = require('child_process');
const p = 'Reply with exactly one line formatted as: L3 LEAF: followed by a 10-word tip for PMs using Claude Fable 5. No other text.';
const run = () => new Promise((res, rej) => execFile('claude', ['-p', p, '--model', 'claude-haiku-4-5-20251001', '--allowedTools', 'Bash'], {stdio:['ignore','pipe','pipe'],timeout:600000,encoding:'utf8'}, (e,o) => e?rej(e):res(o.trim().split('\\n')[0])));
Promise.all([run(), run()]).then(([a,b]) => { console.log('L3 OK: '+a); console.log('L3 OK: '+b); }).catch(e => { console.error(String(e)); process.exit(1); });`;

const prompt = `Step 1: Use the Write tool to create the file ${DIR}/wf_L3.js with this exact JavaScript content (verbatim, no changes):
${l3}
Step 2: Use Bash to execute: node ${DIR}/wf_L3.js
Step 3: Your entire response must be exactly one line: L2 OK: followed by the first line of the node output from step 2. No other text.`;

const out = execFileSync('claude', ['-p', prompt, '--model', 'claude-sonnet-4-6', '--allowedTools', 'Bash,Write', '--permission-mode', 'acceptEdits'],
  {stdio: ['ignore','pipe','pipe'], timeout: 600000, encoding: 'utf8'});

console.log(out.trim());
