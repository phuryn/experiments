const { execFileSync } = require('child_process');
const L3 = '<WORKDIR>/Temp/output/fable5-n10/recwf-node/r02/wf_L3.js';

const l3src = `const{spawn}=require('child_process');
function h(){return new Promise((res,rej)=>{
const c=spawn('claude',['-p','Output exactly one line: L3 LEAF: then a 10-word tip for PMs using Claude Fable 5',
'--model','claude-haiku-4-5-20251001','--allowedTools','Bash'],
{stdio:['ignore','pipe','pipe'],timeout:600000});
let o='';c.stdout.on('data',d=>o+=d);
c.on('close',()=>res(o.trim().split('\\n')[0]));c.on('error',rej);});}
async function main(){const[r1,r2]=await Promise.all([h(),h()]);
console.log('L3 OK: '+r1);console.log('L3 OK: '+r2);}
main().catch(e=>{console.error(e);process.exit(1);});`;

const prompt = `You are level L2 in a recursive workflow test. Do these steps in order:
1. Write this exact JavaScript to the file ${L3} using your Write tool:
${l3src}
2. Run it with Bash: node ${L3}
3. Your response must include this line: L2 OK: <first line of output from step 2>`;

const out = execFileSync('claude', [
  '-p', prompt,
  '--model', 'claude-sonnet-4-6',
  '--allowedTools', 'Bash,Write',
  '--permission-mode', 'acceptEdits'
], { stdio: ['ignore','pipe','pipe'], timeout: 600000, encoding: 'utf8' });

process.stdout.write(out);
