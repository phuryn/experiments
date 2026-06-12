const {execFile}=require('child_process');
const m='claude-haiku-4-5-20251001';
const p='Reply in one line only: "L3 LEAF: " then a 10-word tip for PMs using Claude Fable 5. No other output.';
function h(){return new Promise((ok,no)=>{
  execFile('claude',['-p',p,'--model',m,'--allowedTools','Bash'],
    {timeout:600000,stdio:['ignore','pipe','pipe']},
    (e,o)=>e?no(e):ok(o.trim().split('\n')[0]));
});}
Promise.all([h(),h()]).then(([a,b])=>{
  console.log('L3 OK: '+a);
  console.log('L3 OK: '+b);
}).catch(e=>{console.error(e);process.exit(1);});
