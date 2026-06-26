<!--
X ARTICLE draft. Firsthand experiment in experiments/managed-agents/ (225 runs + code-defined agent on 2 targets + translator), 2026-06-01.
Thesis: the code-defined agent definition is the durable asset; the runtime (managed-cloud or local) is a swappable deploy target.
Structure from Codex consult. Voice: builder-teacher. No emoji, no em dash. Real numbers only. Honest caveats baked in.
Title argument test: "This piece argues that the agent definition (the repo) is the asset, not the runtime." PASS.
Card: title + subtitle + hero (suggest hero = the "one agent, two runtimes" diagram or the two side-by-side BUG:/FIX: outputs).
-->

# The Agent Is the Repo, Not the Runtime

*I ran one code-defined agent on Google's managed cloud sandbox and on Claude locally. Both caught the same bug. Then I ran 225 tests to measure what the managed loop actually costs.*

---

Google shipped Managed Agents in the Gemini API. One API call: they spin up a Linux sandbox, run the whole agent loop, hand back the result. No orchestration code. It is a clean product.

I tested it firsthand instead of reacting to the launch. Real API, 225 executions, two providers, one afternoon, 57 cents. The data changed the question I think builders should ask about agent platforms.

## One agent, two runtimes

I wrote one small agent definition. A folder with four things:

- instructions (what the agent is)
- a `SKILL.md`: a "bug-finder" skill that says read the spec, run the code, report each bug as `BUG: ... | FIX: ...`
- a `spec.md`: a calculator spec (add and multiply)
- a `solution.py` with a deliberate bug: `mul` actually adds

Then I ran that same definition two ways.

On **Google's Managed Agents**: I mounted the files into the managed sandbox and sent one task. Google's runtime read the files, executed the code in its sandbox, applied the skill, and reported the bug with the one-line fix.

On **Claude, locally**: same instructions, same `SKILL.md`, same files, on my machine. Claude read the files, ran the code, applied the skill, and reported the same bug in the same format.

Two runtimes. One cloud-managed, one local. Two vendors. One definition. Same result.

The runtime was not the agent. The repo was.

## Agent definitions are becoming deployable software

This is the shift hiding inside the launch. The thing you author is no longer a prompt. It is a bundle: instructions, skills, a spec, the files the agent works on, the tools it can call. That bundle is the asset. The runtime is where you deploy it.

Google's Managed Agents is one deploy target: their cloud, their loop, their sandbox. Claude on your laptop is another: your machine, your loop, your files. Gemini called directly is a third. The bundle moved between them without a rewrite.

It is the same point as reviewing artifacts instead of code, one level up. You do not own the generated code, and now you do not own the runtime either. You own the definition that produces the behavior. Keep that portable and the platform question stops being scary.

## What the managed loop costs

"Google runs the loop for you" is the pitch. So I measured the bill.

I ran a battery of tasks 25 times each, on the same model class, two ways: Google's Managed Agents (they run the loop) and the same model self-orchestrated (I run the loop). 225 runs total.

Same model. Same 100% pass rate. But handing Google the loop cost about **5x more** and ran about **4x slower** than orchestrating it myself.

You are renting a sandbox and an agent loop. That is real value when the task needs them: in my compute tasks, the managed runtime actually wrote and executed code in its sandbox. It is pure overhead when the task doesn't: on a plain reasoning task it still cost 3x and ran 4x slower for the same answer.

One honest caveat: every task hit 100% on every runtime, because the tasks were within model capability. So this is a cost, control, and portability finding, not a claim that one runtime is smarter than another. The reliability cliff lives in harder, long-horizon, tool-heavy work, and that is the next test.

## What travels

The portability held everywhere I checked:

- One `AGENTS.md` format rule, fed three runtimes its native way (Google's managed agent, Gemini direct, Claude): 100% compliance on all three.
- One `SKILL.md` skill: applied correctly on Google's managed runtime and on Claude.
- Local files: read on both, Google through mounted sources, Claude through the local filesystem.
- I also built a small Gemini-to-Anthropic adapter so the same request and tool definitions run on either provider. Four out of four live tests passed.

The control surface is portable. Only the runtime underneath it changes.

## Where the runtimes still differ

Portable does not mean identical. The honest gaps:

- **MCP.** Google's free dev endpoint rejected an `mcp_server` tool outright. MCP there lives on the Enterprise (Vertex) path, or you install it into the sandbox at runtime. Claude takes MCP through config or the SDK. Both are code-definable. I did not wire a live MCP server in this round.
- **Secrets.** Google's model is sharp: secrets never sit inside the sandbox. Credentials are injected at an egress proxy on the way out, so the agent can use a token it can never read. Locally, you hold the secrets yourself.
- **Subagents.** Not exposed in Google's Managed Agents. Claude has them.
- **UI.** Google gives you a studio. Anthropic gives you none, on purpose. If the definition is code, a UI is optional. The code-only path is the honest version of the same idea.

## The question that actually matters

If you need a managed cloud sandbox, isolation, or an enterprise integration path, Google's runtime is genuinely interesting. If you care about cost, latency, control, and inspectability, own the loop and treat managed runtimes as one deploy target among several.

Either way, the platform question most people ask is the wrong one. Not "which agent platform do I build on." Ask: **can my agent definition survive changing runtimes?** If yes, you are free. If no, you bought a cage with a nice UI.

## Honest limits

- Tasks were within model capability, so no reliability-cliff claim.
- No live MCP server wired in this round.
- Google's secret-injection field is accepted on the dev endpoint, but I could not confirm the injection there (it looks Enterprise-bound).
- This is one reproducible battery from one afternoon, not a universal benchmark.

## The whole thing cost 57 cents

225 executions, two providers, a translator, and the code-defined agent that ran on both. The harness, the translator, and every run log are in a repo. Inspect the artifacts. Do not trust the screenshots.

Rent the runtime if it saves you time. Own the definition. That is the part that is yours.
