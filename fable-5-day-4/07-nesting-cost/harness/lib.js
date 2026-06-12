// Set 06 shared harness (port of v1 lib.js): retries, prompts, claude runner.
const { spawn } = require('child_process');
const fs = require('fs');

const REPO = '<WORKDIR>';
const MONTHS = ['202603', '202604', '202605', '202606'];

const leafPrompt = (m) => `You are analyzing real X/Twitter post performance data for a content system.

Read knowledge/posts/db_${m}.csv. Columns: date, platform, author, handle, post_id, url, title_or_hook, keywords, likes, retweets, bookmarks, views, comments, template, voice, notes.

Produce a markdown analysis (~350 words) with exactly these sections:
1. **Top hook patterns** — the 4-5 hook patterns with the best engagement this month (use bookmarks-per-like ratio and views; quote 2-3 example hooks verbatim with their numbers).
2. **Underperformers** — 2-3 hook or format patterns that underperform, with numbers.
3. **Pawel vs field** — anything notable about author "Pawel Huryn" rows compared to other authors in the file (if no Pawel rows, say so).
4. **One hypothesis** — a single testable hypothesis this month's data suggests.

Be specific. Cite real numbers from the file. Output ONLY the markdown analysis.`;

const synthPrompt = (dir) => `You are synthesizing four monthly analyses of X/Twitter post performance into one report for Pawel Huryn.

Read these four files: ${MONTHS.map((m) => `${dir}/leaf_${m}.md`).join(', ')}.

Produce a final markdown report (~500 words):
1. **Durable patterns** — hook/format patterns that recur across 2+ months (cross-month signal, not one-month noise). Cite which months and numbers.
2. **Three actionable recommendations** for Pawel's next 10 posts, each tied to evidence.
3. **Two hypotheses worth testing**, each with the supporting numbers.

Output ONLY the markdown report.`;

function runOnce({ prompt, model, allowedTools, maxTurns, timeoutMs, label }) {
  return new Promise((resolve, reject) => {
    const t0 = Date.now();
    const args = ['-p', prompt, '--model', model, '--output-format', 'json',
      '--allowedTools', allowedTools, '--max-turns', String(maxTurns)];
    const child = spawn('claude', args, {
      cwd: REPO,
      env: { ...process.env },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let out = '', err = '';
    const killer = setTimeout(() => { child.kill('SIGKILL'); }, timeoutMs);
    child.stdout.on('data', (d) => { out += d; });
    child.stderr.on('data', (d) => { err += d; });
    child.on('error', (e) => { clearTimeout(killer); reject(new Error(`${label} spawn error: ${e.message}`)); });
    child.on('close', (code) => {
      clearTimeout(killer);
      const wall = (Date.now() - t0) / 1000;
      if (code !== 0) return reject(new Error(`${label} exit ${code}: ${err.slice(0, 500)}`));
      try {
        const j = JSON.parse(out);
        resolve({ label, wall, cost: j.total_cost_usd, turns: j.num_turns, usage: j.usage, result: j.result });
      } catch (e) {
        reject(new Error(`${label} bad JSON: ${out.slice(0, 300)}`));
      }
    });
  });
}

async function runClaude(opts) {
  for (let attempt = 1; ; attempt++) {
    try {
      return await runOnce(opts);
    } catch (e) {
      if (attempt >= 3) throw e;
      console.error(`retry ${attempt} for ${opts.label}: ${e.message}`);
      await new Promise((r) => setTimeout(r, 3000 * attempt));
    }
  }
}

module.exports = { REPO, MONTHS, leafPrompt, synthPrompt, runClaude, fs };
