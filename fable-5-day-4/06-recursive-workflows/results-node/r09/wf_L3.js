const { Worker, isMainThread, parentPort } = require('worker_threads');
const { execFileSync } = require('child_process');

if (!isMainThread) {
  try {
    const result = execFileSync(
      'claude',
      ['-p', 'Output exactly one line in this format: L3 LEAF: <10-word tip for PMs using Claude Fable 5>', '--model', 'claude-haiku-4-5-20251001', '--allowedTools', 'Bash'],
      { stdio: ['ignore', 'pipe', 'pipe'], timeout: 600000, encoding: 'utf8' }
    );
    parentPort.postMessage(result.trim().split('\n')[0]);
  } catch (e) {
    parentPort.postMessage('L3 LEAF: error ' + e.message.slice(0, 40));
  }
} else {
  const messages = [];
  for (let i = 0; i < 2; i++) {
    const worker = new Worker(__filename);
    worker.on('message', (msg) => {
      messages.push(msg);
      console.log('L3 OK: ' + msg);
    });
  }
}
