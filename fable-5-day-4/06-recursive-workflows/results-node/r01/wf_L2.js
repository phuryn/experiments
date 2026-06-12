const {execFileSync}=require('child_process');
const WF3=__dirname.replace(/\\/g,'/')+'/wf_L3.js';
const wf3=`const {execFile}=require('child_process');
const m='claude-haiku-4-5-20251001';
const p='Reply in one line only: "L3 LEAF: " then a 10-word tip for PMs using Claude Fable 5. No other output.';
function h(){return new Promise((ok,no)=>{
  execFile('claude',['-p',p,'--model',m,'--allowedTools','Bash'],
    {timeout:600000,stdio:['ignore','pipe','pipe']},
    (e,o)=>e?no(e):ok(o.trim().split('\\n')[0]));
});}
Promise.all([h(),h()]).then(([a,b])=>{
  console.log('L3 OK: '+a);
  console.log('L3 OK: '+b);
}).catch(e=>{console.error(e);process.exit(1);});`;
const prompt=`You are L2. Do exactly:
1. Write this exact content (between the markers, not including the markers) to ${WF3}:
---BEGIN---
${wf3}
---END---
2. Run: node "${WF3}"
3. Print exactly one line: L2 OK: <first line of the node output>
No other output.`;
const out=execFileSync('claude',['-p',prompt,'--model','claude-sonnet-4-6',
  '--allowedTools','Bash,Write','--permission-mode','acceptEdits'],
  {stdio:['ignore','pipe','pipe'],timeout:600000});
console.log(out.toString().trim());
