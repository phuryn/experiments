const { execFileSync } = require("child_process");

const dir = "<WORKDIR>/Temp/output/fable5-n10/recwf-node/r06";
const l3 = dir + "/wf_L3.js";
const haikuTip = "Output exactly one line starting with L3 LEAF: then give a 10-word tip for PMs using Claude Fable 5";
const l3code =
  'const{spawn}=require("child_process");\n' +
  'const tip="' + haikuTip + '";\n' +
  'const go=()=>new Promise((res,rej)=>{let o="";\n' +
  'const p=spawn("claude",["-p",tip,"--model","claude-haiku-4-5-20251001","--allowedTools","Bash"],{stdio:["ignore","pipe","pipe"]});\n' +
  'p.stdout.on("data",d=>o+=d);p.on("close",()=>res(o.trim().split("\\n")[0]));p.on("error",rej);});\n' +
  'Promise.all([go(),go()]).then(rs=>rs.forEach(r=>console.log("L3 OK: "+r)));';

const prompt =
  "You are L2. Do these steps in order:\n" +
  "1. Use the Write tool to write exactly this content to " + l3 + ":\n" + l3code +
  "\n2. Use Bash tool to run: node " + l3 +
  "\n3. Your final output line must be exactly: L2 OK: <first line of node output>";

const out = execFileSync("claude", [
  "-p", prompt,
  "--model", "claude-sonnet-4-6",
  "--allowedTools", "Bash,Write",
  "--permission-mode", "acceptEdits"
], { stdio: ["ignore", "pipe", "pipe"], timeout: 600000, encoding: "utf8" });

const l2line = out.split("\n").find(l => l.startsWith("L2 OK:")) || out.trim().split("\n").pop();
console.log(l2line);
