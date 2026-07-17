# 02 — Day-one capacity: the same cell scored 0 and then 14/14

**Question:** On launch night, two of Kimi K3's eight cells never finished. The obvious write-up is "K3 failed two tasks." Is that true — or is a day-one benchmark measuring the provider's capacity rather than the model's capability?

**Method:** Re-run the two failed cells against the identical model, task, prompt, harness and target repo, 13 hours after the launch-night attempt. Nothing changed but the clock. The implement cell is graded deterministically by 14 hidden `bun test` cases it never sees ([prompts/T6-implement-to-spec.md](prompts/T6-implement-to-spec.md), [grades_T6_kimi.json](grades_T6_kimi.json)). Availability was probed separately against **both** of Moonshot's own routes and OpenRouter.

Runners: [harness/run_kimi_t6_only.py](harness/run_kimi_t6_only.py), [harness/run_kimi_t7_direct.py](harness/run_kimi_t7_direct.py). Proxies: [harness/kimi_proxy.py](harness/kimi_proxy.py) (original), [harness/kimi_proxy2.py](harness/kimi_proxy2.py) (fixed — see finding 3). Raw upstream log: [throttle.log](throttle.log).

**Results — the implement cell, same everything, 13 hours apart:**

| | Launch night (Jul 16, ~01:00) | Re-run (Jul 17, 07:41) |
|---|---|---|
| Tokens served | **0** | 22,443 |
| Assistant turns | 1 (one narration line) | 44 |
| Wall | died at 0s | 1,447.9s, clean `exit=0` |
| Hidden tests passed | **DNF** | **14 / 14** |

On launch night the endpoint returned *nothing*. Not a wrong answer — no tokens at all.

**Results — availability probes, ~13h after launch:**

| Route | Result |
|---|---|
| Moonshot `api.moonshot.ai/v1/chat/completions` (first-party key) | 5 / 6 succeeded, 1x `429 engine_overloaded_error` |
| Moonshot `api.moonshot.ai/anthropic` (first-party key, small probe) | intermittent, ~50% `429 engine_overloaded_error` |
| Moonshot `/anthropic` driving the real Claude Code CLI | **could not complete a single `claude -p "say alive"` in 5 minutes** |
| OpenRouter `moonshotai/kimi-k3` | serves, but throttles heavily under agentic load |

A 90-token probe lands. A real agentic request — large system prompt plus tool definitions — does not.

**Results — the stale-docs cell: five attempts, never finished:**

| Attempt | Outcome |
|---|---|
| Launch night x2 | timeout (25 min, 40 min caps) |
| Jul 17, 08:10 | `api_error` at 125s, 8 turns |
| Jul 17, 08:13 | `api_error` at 267s, 28 turns |
| Jul 17, 08:44 (fixed proxy, 2h ceiling) | **"Request timed out"** at 4,032s, 9 turns, after the proxy absorbed **162** throttles |

**Findings:**

1. **The same cell scored DNF and then 14/14 with only the clock changed.** Same model, same task, same prompt, same harness. The launch-night failure carried no information about the model at all. Any day-one benchmark run against a saturated endpoint is partly measuring queue depth.
2. **The bottleneck is Moonshot's own capacity, not a reseller's free tier.** A direct first-party key returns `engine_overloaded_error` too. This is not an OpenRouter story — and at 2.8T parameters, there is no self-hosting fallback either: the weights being open does not make the model runnable.
3. **A throttle can arrive disguised as a success, and that is what killed the longest cell.** OpenRouter does not always signal rate-limiting with an HTTP 429. Under load it returns **HTTP 200** with the error inside the SSE body:

   ```
   event: ping
   data: {"type":"ping"}
   event: error
   data: {"type":"error","error":{"type":"rate_limit_error",
          "message":"Provider returned error","error_type":"rate_limit_exceeded"}}
   ```

   The original shim retried on HTTP *status* only (429/5xx), so a 200-wrapped throttle was forwarded to the CLI as a valid response; the CLI then saw a stream containing nothing but an error event and aborted the whole run with `"API returned an empty or malformed response (HTTP 200)"`. The stale-docs task is the longest tool chain in the battery, so it takes the most exposure — which is exactly why it died every run while shorter cells landed. [kimi_proxy2.py](harness/kimi_proxy2.py) peeks the first chunk before committing the 200 and retries 200-wrapped error events like 429s. In one 67-minute run it absorbed **162** of them ([throttle.log](throttle.log)).
4. **Fixing the shim was not enough.** With 200-wrapped throttles retried, the cell got far past its old death point (9-28 turns became a 67-minute run) and still timed out. The pool is simply too hot. **The stale-docs cell stays DNF** — a capacity result, honestly reported, not a model score.
5. **Two wrong diagnoses preceded the right one, and both are recorded here rather than quietly corrected.** First: "it timed out under throttle" (it did not; it errored at 125s). Second, worse: "only 3x 429 in the window, so throttle is *not* the blocker — this is our own harness, label the cell *not measured*." That was backwards, and it briefly shipped in a chart. The 429 count was measuring the wrong thing, because the throttles were arriving as 200s. The root cause was only found by **logging the raw upstream first chunk instead of theorizing about it.**

**Caveats:**

- **n=1 per cell**, plus a 6-attempt availability probe. Directional.
- The throttle is a **moving target**. These numbers describe July 16–17, 2026. Moonshot's capacity will change, and this experiment expires quickly by design — that is the point of it.
- **The re-run is not a controlled experiment.** 13 hours passed; the endpoint's load is unobserved and uncontrolled. The claim is narrow: the same cell produced no tokens and then a perfect score, so the first result was not about the model.
- The proxy fix is **infrastructure resilience only** — it retries transport errors. It cannot change what the model computes, and it does not touch the prompt, tools, task or model. It cannot flatter a score.
- `kimi_proxy2.py` also sets `--reasoning-effort max`, matching Moonshot's documented contract (`max` is the only supported level; "do not use the K2.x thinking parameter"). The other K3 cells ran without that flag. The stale-docs cell never produced a score, so this never affected a published number — but it is a transport difference and is disclosed here.
- **De-identified.** The target app is private. Raw model reports quote it and are **withheld**; `throttle.log` is upstream API status lines only, and the grades JSON is content-free. Both prompts are self-contained specs, published verbatim.
- If a number here and a post disagree, the data here wins: [@PawelHuryn](https://x.com/PawelHuryn).

**Source post:** [@PawelHuryn on X](https://x.com/i/status/2078039188834783367)
