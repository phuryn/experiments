const { execFile } = require('child_process');

const prompt = 'Reply in exactly one line. Format: L3 LEAF: then a 10-word tip for PMs using Claude Fable 5. No other output.';

const opts = {
  stdio: ['ignore', 'pipe', 'pipe'],
  timeout: 600000,
  encoding: 'utf8'
};

function runClaude(cb) {
  execFile('claude', ['-p', prompt, '--model', 'claude-haiku-4-5-20251001', '--allowedTools', 'Bash'], opts, cb);
}

let results = [];
let done = 0;

function onDone() {
  done++;
  if (done === 2) {
    results.forEach(r => {
      const firstLine = r.split('\n')[0].trim();
      console.log('L3 OK: ' + firstLine);
    });
  }
}

runClaude((err, stdout) => {
  results[0] = err ? ('ERROR: ' + err.message) : stdout;
  onDone();
});

runClaude((err, stdout) => {
  results[1] = err ? ('ERROR: ' + err.message) : stdout;
  onDone();
});
