const { execFile } = require('child_process');
const p = 'Reply with exactly one line formatted as: L3 LEAF: followed by a 10-word tip for PMs using Claude Fable 5. No other text.';
const run = () => new Promise((res, rej) => execFile('claude', ['-p', p, '--model', 'claude-haiku-4-5-20251001', '--allowedTools', 'Bash'], {stdio:['ignore','pipe','pipe'],timeout:600000,encoding:'utf8'}, (e,o) => e?rej(e):res(o.trim().split('\n')[0])));
Promise.all([run(), run()]).then(([a,b]) => { console.log('L3 OK: '+a); console.log('L3 OK: '+b); }).catch(e => { console.error(String(e)); process.exit(1); });