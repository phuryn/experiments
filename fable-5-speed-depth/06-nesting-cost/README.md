# Fable 5 experiment receipts (3/3): what nesting costs (flat vs nested, two runs)

Same job both ways. Flat: a zero-token Node harness fans out to 4 haiku leaves
(one per CSV of real post-performance data) plus 1 sonnet synthesis. Nested: a
sonnet manager writes its own inner orchestrator, runs the same 4 leaves, and
synthesizes itself. Result on the real workload: nested = 1.63x cost, 1.64x wall;
on the earlier toy task: 1.84x / 1.87x. Receipts below are verbatim CLI JSON.
Companion to: Claude Fable 5 for PMs: The Ultimate Guide, Section 7.4.

## lib.js (shared harness: retries, prompts)

```js
const { spawn } = require('child_process');
const fs = require('fs');

const MONTHS = ['202603', '202604', '202605', '202606'];

const leafPrompt = (m) => `You are analyzing real X/Twitter post performance data for a content system.

Read the month's post-performance CSV (path genericized for publishing). Columns: standard engagement metrics (date, platform, likes, retweets, bookmarks, views, comments) plus a few internal content-tagging columns (genericized).

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
      cwd: '/path/to/repo',
      env: { ...process.env, IS_SANDBOX: '1' },
      stdio: ['ignore', 'pipe', 'pipe'],
    });
    let out = '', err = '';
    const killer = setTimeout(() => { child.kill('SIGKILL'); }, timeoutMs);
    child.stdout.on('data', (d) => { out += d; });
    child.stderr.on('data', (d) => { err += d; });
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

module.exports = { MONTHS, leafPrompt, synthPrompt, runClaude, fs };
```

## flat.js (flat arm)

```js
// Flat workflow: L0 harness (this file, 0 tokens) -> 4 haiku leaves in parallel -> 1 sonnet synthesis.
const { MONTHS, leafPrompt, synthPrompt, runClaude, fs } = require('./lib');
const DIR = '/path/to/repo/Temp/scripts/workflow-real/flat-out';
fs.mkdirSync(DIR, { recursive: true });

(async () => {
  const t0 = Date.now();
  const leaves = await Promise.all(MONTHS.map((m) =>
    runClaude({ prompt: leafPrompt(m), model: 'haiku', allowedTools: 'Read', maxTurns: 8, timeoutMs: 360000, label: `leaf_${m}` })
  ));
  for (const l of leaves) fs.writeFileSync(`${DIR}/${l.label}.md`, l.result);
  const synth = await runClaude({ prompt: synthPrompt(DIR), model: 'sonnet', allowedTools: 'Read', maxTurns: 10, timeoutMs: 360000, label: 'synthesis' });
  fs.writeFileSync(`${DIR}/final-report.md`, synth.result);
  const wall = (Date.now() - t0) / 1000;
  const receipts = [...leaves, synth].map(({ result, ...r }) => r);
  const total = receipts.reduce((s, r) => s + r.cost, 0);
  fs.writeFileSync(`${DIR}/receipts.json`, JSON.stringify({ arm: 'flat', wall, total, receipts }, null, 2));
  console.log(JSON.stringify({ arm: 'flat', wall, total, receipts }, null, 2));
})().catch((e) => { console.error(e.message); process.exit(1); });
```

## nested.js (nested arm: manager writes inner.js)

```js
// Nested workflow: 1 sonnet manager writes+runs its own harness over 4 haiku leaves, then synthesizes itself.
const { MONTHS, leafPrompt, runClaude, fs } = require('./lib');
const DIR = '/path/to/repo/Temp/scripts/workflow-real/nested-out';
fs.mkdirSync(`${DIR}/receipts`, { recursive: true });
for (const m of MONTHS) fs.writeFileSync(`${DIR}/leaf_prompt_${m}.txt`, leafPrompt(m));

const managerPrompt = `You are a workflow orchestrator running a real analysis pipeline. Work from /path/to/repo.

Goal: produce a cross-month hook-pattern performance report at ${DIR}/final-report.md.

Steps:
1. Write a Node.js harness at ${DIR}/inner.js that spawns FOUR \`claude -p\` agents IN PARALLEL, one per month: 202603, 202604, 202605, 202606. For each month m, the prompt is EXACTLY the contents of ${DIR}/leaf_prompt_<m>.txt (read the file in the harness and pass its contents as the -p argument). Flags per agent: --model haiku --output-format json --allowedTools Read --max-turns 8. Spawn with env IS_SANDBOX=1, stdin ignored ('ignore'), maxBuffer 64MB, 360000ms timeout, cwd /path/to/repo. Parse each agent's JSON stdout; save the full JSON to ${DIR}/receipts/leaf_<m>.json and its .result field to ${DIR}/leaf_<m>.md.
2. Run the harness with Bash: node ${DIR}/inner.js
3. Read the four leaf_*.md analyses and synthesize the final report YOURSELF — do not spawn another agent for synthesis. Write ${DIR}/final-report.md (~500 words): 1) **Durable patterns** recurring across 2+ months, with months and numbers; 2) **Three actionable recommendations** for Pawel's next 10 posts, each tied to evidence; 3) **Two hypotheses worth testing**, each with supporting numbers.

Hard budget: exactly 4 claude calls total, all spawned by the harness. No retries unless a leaf returns malformed JSON. When done, reply with one line: DONE.`;

(async () => {
  const t0 = Date.now();
  const mgr = await runClaude({ prompt: managerPrompt, model: 'sonnet', allowedTools: 'Bash,Write,Read', maxTurns: 40, timeoutMs: 1200000, label: 'manager' });
  const wall = (Date.now() - t0) / 1000;
  const leafReceipts = MONTHS.map((m) => {
    const j = JSON.parse(fs.readFileSync(`${DIR}/receipts/leaf_${m}.json`, 'utf8'));
    return { label: `leaf_${m}`, wall: j.duration_ms / 1000, cost: j.total_cost_usd, turns: j.num_turns, usage: j.usage };
  });
  const { result, ...mgrR } = mgr;
  const receipts = [mgrR, ...leafReceipts];
  const total = receipts.reduce((s, r) => s + r.cost, 0);
  fs.writeFileSync(`${DIR}/receipts.json`, JSON.stringify({ arm: 'nested', wall, total, receipts }, null, 2));
  console.log(JSON.stringify({ arm: 'nested', wall, total, receipts }, null, 2));
})().catch((e) => { console.error(e.message); process.exit(1); });
```

## flat-out/receipts.json

```json
{
  "arm": "flat",
  "wall": 128.048,
  "total": 0.38370345000000006,
  "receipts": [
    {
      "label": "leaf_202603",
      "wall": 76.374,
      "cost": 0.138075,
      "turns": 4,
      "usage": {
        "input_tokens": 28,
        "cache_creation_input_tokens": 33302,
        "cache_read_input_tokens": 78960,
        "output_tokens": 3722,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 33302,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 10,
            "output_tokens": 3370,
            "cache_read_input_tokens": 18330,
            "cache_creation_input_tokens": 11764,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 11764
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      }
    },
    {
      "label": "leaf_202604",
      "wall": 47.398,
      "cost": 0.056092649999999994,
      "turns": 5,
      "usage": {
        "input_tokens": 42,
        "cache_creation_input_tokens": 14751,
        "cache_read_input_tokens": 165519,
        "output_tokens": 4212,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 14751,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 8,
            "output_tokens": 1740,
            "cache_read_input_tokens": 38181,
            "cache_creation_input_tokens": 6885,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 6885
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      }
    },
    {
      "label": "leaf_202605",
      "wall": 56.855,
      "cost": 0.046767249999999996,
      "turns": 2,
      "usage": {
        "input_tokens": 18,
        "cache_creation_input_tokens": 6981,
        "cache_read_input_tokens": 60630,
        "output_tokens": 6392,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 6981,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 8,
            "output_tokens": 6240,
            "cache_read_input_tokens": 30315,
            "cache_creation_input_tokens": 6981,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 6981
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      }
    },
    {
      "label": "leaf_202606",
      "wall": 36.952,
      "cost": 0.031226000000000004,
      "turns": 2,
      "usage": {
        "input_tokens": 18,
        "cache_creation_input_tokens": 4932,
        "cache_read_input_tokens": 60630,
        "output_tokens": 3796,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 4932,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 8,
            "output_tokens": 3595,
            "cache_read_input_tokens": 30315,
            "cache_creation_input_tokens": 4932,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 4932
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      }
    },
    {
      "label": "synthesis",
      "wall": 51.674,
      "cost": 0.11154254999999999,
      "turns": 5,
      "usage": {
        "input_tokens": 4,
        "cache_creation_input_tokens": 16621,
        "cache_read_input_tokens": 47306,
        "output_tokens": 2334,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 16621,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 1,
            "output_tokens": 2049,
            "cache_read_input_tokens": 29551,
            "cache_creation_input_tokens": 4825,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 4825
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      }
    }
  ]
}
```

## nested-out/receipts.json

```json
{
  "arm": "nested",
  "wall": 209.441,
  "total": 0.624506,
  "receipts": [
    {
      "label": "manager",
      "wall": 209.441,
      "cost": 0.1980531,
      "turns": 10,
      "usage": {
        "input_tokens": 8,
        "cache_creation_input_tokens": 21554,
        "cache_read_input_tokens": 180772,
        "output_tokens": 4198,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 21554,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 1,
            "output_tokens": 5,
            "cache_read_input_tokens": 36839,
            "cache_creation_input_tokens": 2470,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 2470
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      }
    },
    {
      "label": "leaf_202603",
      "wall": 122.308,
      "cost": 0.30398094999999997,
      "turns": 9,
      "usage": {
        "input_tokens": 54,
        "cache_creation_input_tokens": 99167,
        "cache_read_input_tokens": 158317,
        "output_tokens": 5206,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 99167,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 8,
            "output_tokens": 3007,
            "cache_read_input_tokens": 30886,
            "cache_creation_input_tokens": 30635,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 30635
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      }
    },
    {
      "label": "leaf_202604",
      "wall": 61.938,
      "cost": 0.0718837,
      "turns": 7,
      "usage": {
        "input_tokens": 58,
        "cache_creation_input_tokens": 11724,
        "cache_read_input_tokens": 235557,
        "output_tokens": 6723,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 11724,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 8,
            "output_tokens": 1054,
            "cache_read_input_tokens": 39874,
            "cache_creation_input_tokens": 2165,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 2165
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      }
    },
    {
      "label": "leaf_202605",
      "wall": 24.789,
      "cost": 0.0246735,
      "turns": 2,
      "usage": {
        "input_tokens": 18,
        "cache_creation_input_tokens": 6994,
        "cache_read_input_tokens": 60630,
        "output_tokens": 1970,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 6994,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 8,
            "output_tokens": 1805,
            "cache_read_input_tokens": 30315,
            "cache_creation_input_tokens": 6994,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 6994
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      }
    },
    {
      "label": "leaf_202606",
      "wall": 35.171,
      "cost": 0.02591475,
      "turns": 2,
      "usage": {
        "input_tokens": 18,
        "cache_creation_input_tokens": 4983,
        "cache_read_input_tokens": 60630,
        "output_tokens": 2721,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 4983,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 8,
            "output_tokens": 2469,
            "cache_read_input_tokens": 30315,
            "cache_creation_input_tokens": 4983,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 4983
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      }
    }
  ]
}
```

## toy run results.json (ultracode-nesting, 1.84x)

```json
{
  "startedAt": "2026-06-10T05:01:59.330Z",
  "calls": [
    {
      "label": "branchA-orchestrator(sonnet,L1)",
      "ms": 46980,
      "killed": false,
      "err": null,
      "result": "Theme 1 — Decision fatigue: Too many services create paralysis rather than choice, eroding the leisure time they pay for.\nTheme 2 — Continuity failure: Broken cross-device sync turns resuming a show into manual labor, week after week.\nTheme 3 — Visibility gap: No unified view of subscriptions and spending lets costs accumulate invisibly, producing a feeling of being cheated.",
      "usage": {
        "input_tokens": 8,
        "cache_creation_input_tokens": 14047,
        "cache_read_input_tokens": 172351,
        "output_tokens": 1363,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 14047,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 1,
            "output_tokens": 94,
            "cache_read_input_tokens": 31560,
            "cache_creation_input_tokens": 242,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 242
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      },
      "cost_usd": 0.12587155,
      "num_turns": 8,
      "duration_api_ms": 27159,
      "stderr": "Warning: no stdin data received in 3s, proceeding without it. If piping from a slow command, redirect stdin explicitly: < /dev/null to skip, or wait longer.\n"
    },
    {
      "label": "branchB-orchestrator(sonnet,L1)",
      "ms": 57604,
      "killed": false,
      "err": null,
      "result": "The Exhausted Couple: decision fatigue across too many options destroys the shared viewing moment before it starts. The Commuter: broken cross-device sync turns every return home into a manual scrubbing session. The Accidental Subscriber: invisible recurring charges accumulate undetected until a forced financial audit triggers genuine anger. Common root: streaming abundance creates friction and opacity, not ease.",
      "usage": {
        "input_tokens": 8,
        "cache_creation_input_tokens": 14034,
        "cache_read_input_tokens": 172298,
        "output_tokens": 1336,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 14034,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 1,
            "output_tokens": 86,
            "cache_read_input_tokens": 31557,
            "cache_creation_input_tokens": 232,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 232
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      },
      "cost_usd": 0.1253949,
      "num_turns": 8,
      "duration_api_ms": 40386,
      "stderr": "Warning: no stdin data received in 3s, proceeding without it. If piping from a slow command, redirect stdin explicitly: < /dev/null to skip, or wait longer.\n"
    },
    {
      "label": "judge(haiku,L1)",
      "ms": 28804,
      "killed": false,
      "err": null,
      "result": "WINNER: A because it presents discrete, independently prioritizable problems that a PM can measure and scope separately, whereas B bundles each problem with persona narrative and editorial framing that over-specifies the solution before the prioritization question is answered.",
      "usage": {
        "input_tokens": 10,
        "cache_creation_input_tokens": 12124,
        "cache_read_input_tokens": 18330,
        "output_tokens": 1932,
        "server_tool_use": {
          "web_search_requests": 0,
          "web_fetch_requests": 0
        },
        "service_tier": "standard",
        "cache_creation": {
          "ephemeral_1h_input_tokens": 12124,
          "ephemeral_5m_input_tokens": 0
        },
        "inference_geo": "not_available",
        "iterations": [
          {
            "input_tokens": 10,
            "output_tokens": 1932,
            "cache_read_input_tokens": 18330,
            "cache_creation_input_tokens": 12124,
            "cache_creation": {
              "ephemeral_5m_input_tokens": 0,
              "ephemeral_1h_input_tokens": 12124
            },
            "type": "message"
          }
        ],
        "speed": "standard"
      },
      "cost_usd": 0.027422,
      "num_turns": 1,
      "duration_api_ms": 24636,
      "stderr": "Warning: no stdin data received in 3s, proceeding without it. If piping from a slow command, redirect stdin explicitly: < /dev/null to skip, or wait longer.\n"
    }
  ],
  "totalMs": 86412,
  "verdict": "WINNER: A because it presents discrete, independently prioritizable problems that a PM can measure and scope separately, whereas B bundles each problem with persona narrative and editorial framing that over-specifies the solution before the prioritization question is answered."
}
```

