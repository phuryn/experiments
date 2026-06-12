const {execFile}=require('child_process');
function run(){
  return new Promise((res,rej)=>{
    execFile('claude',['-p','Output one line only in this exact format: L3 LEAF: followed by a 10-word tip for PMs using Claude Fable 5','--model','claude-haiku-4-5-20251001','--allowedTools','Bash'],
      {stdio:['ignore','pipe','pipe'],timeout:600000},
      (e,o)=>e?rej(e):res(o.toString().trim().split('\n')[0]));
  });
}
Promise.all([run(),run()]).then(([a,b])=>{
  console.log('L3 OK: '+a);
  console.log('L3 OK: '+b);
});
