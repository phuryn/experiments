const { execFileSync } = require('child_process');
const DIR = '<WORKDIR>/Temp/output/fable5-n10/recwf-node/r07';
const L3 = DIR + '/wf_L3.js';
const l3 = [
  "const{spawn}=require('child_process');",
  "function run(){return new Promise((res,rej)=>{",
  "const p=spawn('claude',['-p','Reply in one line: L3 LEAF: <a 10-word tip for PMs using Claude Fable 5>. Nothing else.','--model','claude-haiku-4-5-20251001','--allowedTools','Bash'],{stdio:['ignore','pipe','pipe']});",
  "let o='';p.stdout.on('data',d=>o+=d);",
  "p.on('close',c=>{if(c===0)res(o.trim().split('\\n')[0]);else rej(new Error('exit '+c));});});}",
  "Promise.all([run(),run()]).then(([a,b])=>{console.log('L3 OK: '+a);console.log('L3 OK: '+b);}).catch(e=>{console.error(e);process.exit(1);});"
].join('\n');
const prompt = `You are L2. Do exactly:\n1. Write file ${L3} with this exact content:\n${l3}\n\n2. Bash: node ${L3}\n\n3. Reply ONLY: L2 OK: [first line of node output]`;
const out = execFileSync('claude', [
  '-p', prompt,
  '--model', 'claude-sonnet-4-6',
  '--allowedTools', 'Bash,Write',
  '--permission-mode', 'acceptEdits'
], { stdio: ['ignore', 'pipe', 'pipe'], timeout: 580000, encoding: 'utf8' });
process.stdout.write(out);
