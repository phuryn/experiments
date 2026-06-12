'use strict';
const { execFileSync } = require('child_process');
const dir = '<WORKDIR>/Temp/output/fable5-n10/recwf-node/r03';
const f3 = dir + '/wf_L3.js';
const hm = 'claude-haiku-4-5-20251001';
const src3 = `const{spawn}=require('child_process');
const P='Respond with exactly one line: L3 LEAF: followed by a 10-word tip for PMs using Claude Fable 5. Nothing else.';
function h(){return new Promise((res,rej)=>{
  const p=spawn('claude',['-p',P,'--model','${hm}','--allowedTools','Bash'],{stdio:['ignore','pipe','pipe'],timeout:600000});
  let o='';p.stdout.on('data',d=>o+=d.toString());
  p.on('close',c=>c===0?res(o.trim().split('\\n')[0]):rej(new Error('exit '+c)));
  p.on('error',rej);
});}
Promise.all([h(),h()]).then(([a,b])=>{
  console.log('L3 OK: '+a);console.log('L3 OK: '+b);
}).catch(e=>{console.error('L3 ERROR: '+e.message);process.exit(1);});`;
const prompt =
  `Use Write tool to write "${f3}" with this exact content:\n${src3}\n` +
  `Then use Bash tool to run: node "${f3}"\n` +
  `Your entire response must be exactly one line: L2 OK: [first line of node output verbatim]`;
const raw = execFileSync(
  'claude',
  ['-p', prompt, '--model', 'claude-sonnet-4-6', '--allowedTools', 'Bash,Write', '--permission-mode', 'acceptEdits'],
  { stdio: ['ignore', 'pipe', 'pipe'], timeout: 600000, encoding: 'utf8' }
);
const ln = raw.trim().split('\n').find(l => l.startsWith('L2 OK:')) || raw.trim().split('\n')[0];
console.log(ln);
