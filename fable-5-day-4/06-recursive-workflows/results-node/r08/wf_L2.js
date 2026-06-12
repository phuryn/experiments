const { execFileSync } = require('child_process');

const l3 = '<WORKDIR>/Temp/output/fable5-n10/recwf-node/r08/wf_L3.js';
const l3src = `const {execFile}=require('child_process');
function run(){
  return new Promise((res,rej)=>{
    execFile('claude',['-p','Output one line only in this exact format: L3 LEAF: followed by a 10-word tip for PMs using Claude Fable 5','--model','claude-haiku-4-5-20251001','--allowedTools','Bash'],
      {stdio:['ignore','pipe','pipe'],timeout:600000},
      (e,o)=>e?rej(e):res(o.toString().trim().split('\\n')[0]));
  });
}
Promise.all([run(),run()]).then(([a,b])=>{
  console.log('L3 OK: '+a);
  console.log('L3 OK: '+b);
});`;

const prompt = `You are level L2. Follow these steps exactly:
STEP 1: Write the file ${l3} with this exact content (verbatim between <<<START>>> and <<<END>>>):
<<<START>>>
${l3src}
<<<END>>>
STEP 2: Run: node ${l3}
STEP 3: Output exactly one line (replace X with first line of step 2 stdout): L2 OK: X`;

const out = execFileSync('claude', [
  '-p', prompt,
  '--model', 'claude-sonnet-4-6',
  '--allowedTools', 'Bash,Write',
  '--permission-mode', 'acceptEdits'
], { stdio: ['ignore', 'pipe', 'pipe'], timeout: 600000 });

const lines = out.toString().trim().split('\n');
const found = lines.find(l => l.startsWith('L2 OK:')) || lines[lines.length - 1];
console.log(found);
