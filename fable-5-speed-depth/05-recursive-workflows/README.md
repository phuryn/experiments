# Fable 5 experiment receipts (2/3): recursive dynamic workflows

Each level WRITES the orchestration code for the level below it, then runs it.
Two variants: (a) spec-driven bash chain, where the model at level N authors
gen_L(N+1).sh from a shared spec (gen_L3 through gen_L6 below were all written
by the model at the level above, correct on first write); (b) a Node seed where
L1 (sonnet) writes wf_L2.js, whose session writes wf_L3.js (haiku leaves).
Companion to: Claude Fable 5 for PMs: The Ultimate Guide, Section 7.3.

## gen_spec.md (the shared spec every level reads)

```markdown
# Recursive workflow depth test — spec

You are the agent at LEVEL N (N is given in your prompt as LEVEL=N). Follow exactly:

1. Append one line to /path/to/repo/Temp/output/gen-depth.log:
   "L<N>: alive at <HH:MM:SS>, my orchestrator was written by L<N-1>"
2. If N >= 6: append "L<N>: leaf, spec floor reached" to the same log, reply "done", and STOP. Do not write any script.
3. Otherwise, WRITE a new bash script at /path/to/repo/Temp/scripts/gen_L<N+1>.sh (you are authoring the next level's orchestrator) that does exactly:
   - appends "L<N+1>: orchestrator starting" to /path/to/repo/Temp/output/gen-depth.log
   - runs: IS_SANDBOX=1 claude -p "Read /path/to/repo/Temp/scripts/gen_spec.md and execute the procedure with LEVEL=<N+1>" --model sonnet --dangerously-skip-permissions < /dev/null
4. Execute it: bash /path/to/repo/Temp/scripts/gen_L<N+1>.sh
5. Reply "done".

Replace every <N>, <N-1>, <N+1> with actual numbers. Keep the log lines exact.
```

## gen_L3.sh (written by the model at L2)

```bash
#!/usr/bin/env bash
echo "L3: orchestrator starting" >> /path/to/repo/Temp/output/gen-depth.log
IS_SANDBOX=1 claude -p "Read /path/to/repo/Temp/scripts/gen_spec.md and execute the procedure with LEVEL=3" --model sonnet --dangerously-skip-permissions < /dev/null
```

## gen_L4.sh (written by the model at L3)

```bash
#!/usr/bin/env bash
echo "L4: orchestrator starting" >> /path/to/repo/Temp/output/gen-depth.log
IS_SANDBOX=1 claude -p "Read /path/to/repo/Temp/scripts/gen_spec.md and execute the procedure with LEVEL=4" --model sonnet --dangerously-skip-permissions < /dev/null
```

## gen_L5.sh (written by the model at L4)

```bash
#!/usr/bin/env bash
echo "L5: orchestrator starting" >> /path/to/repo/Temp/output/gen-depth.log
IS_SANDBOX=1 claude -p "Read /path/to/repo/Temp/scripts/gen_spec.md and execute the procedure with LEVEL=5" --model sonnet --dangerously-skip-permissions < /dev/null
```

## gen_L6.sh (written by the model at L5)

```bash
#!/usr/bin/env bash
echo "L6: orchestrator starting" >> /path/to/repo/Temp/output/gen-depth.log
IS_SANDBOX=1 claude -p "Read /path/to/repo/Temp/scripts/gen_spec.md and execute the procedure with LEVEL=6" --model sonnet --dangerously-skip-permissions < /dev/null
```

## gen-depth.log (run receipt)

```
L2: alive at 10:27:16, my orchestrator was written by L1
L3: orchestrator starting
L3: alive at 10:27:39, my orchestrator was written by L2
L4: orchestrator starting
L4: alive at 10:27:57, my orchestrator was written by L3
L5: orchestrator starting
L5: alive at 10:28:20, my orchestrator was written by L4
L6: orchestrator starting
L6: alive at 10:28:35, my orchestrator was written by L5
L6: leaf, spec floor reached
```

## wf_L1.js (Node variant, human-written seed)

```js
// Recursive dynamic workflow test, L1 (human-written seed).
// Each level's orchestrator for the NEXT level is written by the model at this level.
const { execSync } = require('child_process');
const DIR = '/path/to/repo/Temp/scripts/fable5-recursive-wf';
const t0 = Date.now();
const prompt = `You are workflow level L1 of a recursion experiment. Working dir: ${DIR}.
Your job:
1. Write ${DIR}/wf_L2.js: a Node script that calls "claude -p" (model sonnet, flags: --allowedTools "Bash,Write" --permission-mode acceptEdits) with instructions to act as level L2: L2 must write ${DIR}/wf_L3.js (same pattern, level L3) and run it with node, then print "L2 OK: " plus the first line of L3's output.
2. wf_L3.js is the FLOOR: instead of writing a child, its claude call (model haiku, --allowedTools Bash) must answer in one line: "L3 LEAF: <a 10-word tip for PMs using Claude Fable 5>". wf_L3.js runs TWO such haiku calls in parallel and prints both lines prefixed "L3 OK:".
3. After writing wf_L2.js, run: node ${DIR}/wf_L2.js  and print its full output prefixed "L1 SAW: ".
4. Final line of your output: "L1 OK".
Keep every generated script under 40 lines. Use execSync with stdio pipe and 600000ms timeout.`;
try {
  const out = execSync(`claude -p --model sonnet --allowedTools "Bash,Write" --permission-mode acceptEdits ${JSON.stringify(prompt)}`,
    { encoding: 'utf8', timeout: 580000 });
  console.log(out);
} catch (e) {
  console.log('L1 FAILED:', e.message, (e.stdout||'').slice(-2000));
}
console.log(`WALL: ${((Date.now()-t0)/1000).toFixed(1)}s`);
```

## wf_L2.js (written by L1's model)

```js
const { execSync } = require('child_process');
const dir = '/path/to/repo/Temp/scripts/fable5-recursive-wf';

const prompt = `You are workflow level L2. Do exactly these steps in order:

1. Write the file ${dir}/wf_L3.js with this exact content (under 40 lines):
const { execSync } = require('child_process');
const cmd = 'claude -p \\"Reply in exactly one line. The line must start with: L3 LEAF: followed by a 10-word tip for PMs using Claude Fable 5. Output nothing else.\\" --model claude-haiku-4-5-20251001 --allowedTools Bash';
const r1 = execSync(cmd, { stdio: 'pipe', timeout: 600000 }).toString().trim();
const r2 = execSync(cmd, { stdio: 'pipe', timeout: 600000 }).toString().trim();
console.log('L3 OK: ' + r1);
console.log('L3 OK: ' + r2);

2. Run: node ${dir}/wf_L3.js

3. Print exactly one line: L2 OK: followed by the first line of output from step 2.

Output only that one line. Nothing else.`;

const escaped = prompt.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/`/g, '\\`').replace(/\$/g, '\\$');
const cmd = `claude -p "${escaped}" --model claude-sonnet-4-6 --allowedTools "Bash,Write" --permission-mode acceptEdits`;
const out = execSync(cmd, { stdio: 'pipe', timeout: 600000 }).toString().trim();
process.stdout.write(out + '\n');
```

## wf_L3.js (written by L2's model)

```js
const { execSync } = require('child_process');
const cmd = 'claude -p "Reply in exactly one line. The line must start with: L3 LEAF: followed by a 10-word tip for PMs using Claude Fable 5. Output nothing else." --model claude-haiku-4-5-20251001 --allowedTools Bash';
const r1 = execSync(cmd, { stdio: 'pipe', timeout: 600000 }).toString().trim();
const r2 = execSync(cmd, { stdio: 'pipe', timeout: 600000 }).toString().trim();
console.log('L3 OK: ' + r1);
console.log('L3 OK: ' + r2);
```

## run2.log (Node variant receipt)

```
L2 OK: L3 OK: L3 LEAF: Fable 5 workflows batch parallel research; gather diverse insights simultaneously.

real	0m59.123s
user	0m5.412s
sys	0m1.170s
```

