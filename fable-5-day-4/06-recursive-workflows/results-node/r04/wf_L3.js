const { execFileSync } = require('child_process');
const { Worker, isMainThread, parentPort } = require('worker_threads');
if (!isMainThread) {
  const r = execFileSync('claude', ['-p', 'Reply with exactly one line: L3 LEAF: <a 10-word tip for PMs using Claude Fable 5>', '--model', 'claude-haiku-4-5-20251001', '--allowedTools', 'Bash'], { stdio: ['ignore','pipe','pipe'], timeout: 120000 });
  parentPort.postMessage(r.toString().trim().split('\\n').find(l => l.startsWith('L3 LEAF:')) || r.toString().trim().split('\\n')[0]);
} else {
  const mk = () => new Promise((res, rej) => { const w = new Worker(__filename); w.on('message', res); w.on('error', rej); });
  Promise.all([mk(), mk()]).then(([a, b]) => { console.log('L3 OK: ' + a); console.log('L3 OK: ' + b); }).catch(e => { console.error(e); process.exit(1); });
}
