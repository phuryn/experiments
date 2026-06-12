const{spawn}=require('child_process');
const P='Respond with exactly one line: L3 LEAF: followed by a 10-word tip for PMs using Claude Fable 5. Nothing else.';
function h(){return new Promise((res,rej)=>{
  const p=spawn('claude',['-p',P,'--model','claude-haiku-4-5-20251001','--allowedTools','Bash'],{stdio:['ignore','pipe','pipe'],timeout:600000});
  let o='';p.stdout.on('data',d=>o+=d.toString());
  p.on('close',c=>c===0?res(o.trim().split('\n')[0]):rej(new Error('exit '+c)));
  p.on('error',rej);
});}
Promise.all([h(),h()]).then(([a,b])=>{
  console.log('L3 OK: '+a);console.log('L3 OK: '+b);
}).catch(e=>{console.error('L3 ERROR: '+e.message);process.exit(1);});