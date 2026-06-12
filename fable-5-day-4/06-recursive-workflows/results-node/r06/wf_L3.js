const{spawn}=require("child_process");
const tip="Output exactly one line starting with L3 LEAF: then give a 10-word tip for PMs using Claude Fable 5";
const go=()=>new Promise((res,rej)=>{let o="";
const p=spawn("claude",["-p",tip,"--model","claude-haiku-4-5-20251001","--allowedTools","Bash"],{stdio:["ignore","pipe","pipe"]});
p.stdout.on("data",d=>o+=d);p.on("close",()=>res(o.trim().split("\n")[0]));p.on("error",rej);});
Promise.all([go(),go()]).then(rs=>rs.forEach(r=>console.log("L3 OK: "+r)));