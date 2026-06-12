const{spawn}=require('child_process');
function h(){return new Promise((res,rej)=>{
const c=spawn('claude',['-p','Output exactly one line: L3 LEAF: then a 10-word tip for PMs using Claude Fable 5',
'--model','claude-haiku-4-5-20251001','--allowedTools','Bash'],
{stdio:['ignore','pipe','pipe'],timeout:600000});
let o='';c.stdout.on('data',d=>o+=d);
c.on('close',()=>res(o.trim().split('\n')[0]));c.on('error',rej);});}
async function main(){const[r1,r2]=await Promise.all([h(),h()]);
console.log('L3 OK: '+r1);console.log('L3 OK: '+r2);}
main().catch(e=>{console.error(e);process.exit(1);});
