const{spawn}=require('child_process');
function run(){return new Promise((res,rej)=>{
const p=spawn('claude',['-p','Reply in one line: L3 LEAF: <a 10-word tip for PMs using Claude Fable 5>. Nothing else.','--model','claude-haiku-4-5-20251001','--allowedTools','Bash'],{stdio:['ignore','pipe','pipe']});
let o='';p.stdout.on('data',d=>o+=d);
p.on('close',c=>{if(c===0)res(o.trim().split('\n')[0]);else rej(new Error('exit '+c));});});}
Promise.all([run(),run()]).then(([a,b])=>{console.log('L3 OK: '+a);console.log('L3 OK: '+b);}).catch(e=>{console.error(e);process.exit(1);});
