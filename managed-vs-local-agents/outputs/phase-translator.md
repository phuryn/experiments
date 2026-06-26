# Translator: Gemini <-> Anthropic (API layer)

Live + offline tests. Passed 4/4.

Scope: REST request/response translation (text, system, tools, tool-calls, tool-results, config, finish/stop, usage). Google's managed runtime (loop + sandbox) is explicitly out of scope (see BACKLOG.md).

| Test | Result | Detail |
|------|--------|--------|
| T1 Gemini-format request -> Claude | PASS | translated request ran on Claude; answer='12' |
| T2 Anthropic req -> Gemini -> Anthropic-shaped resp | PASS | round-trip ok; answer='56'; stop_reason=end_turn; usage={'input_tokens': 15, 'output_tokens': 2} |
| T3 Gemini tool-def -> Claude tool_use -> Gemini-shaped call | PASS | Claude called get_weather({'city': 'Paris'}); re-expressed as Gemini functionCall=True |
| T4 Gemini->Anthropic->Gemini schema round-trip preserves tool+role | PASS | structural fidelity check (offline) |

## What this proves
- The same agent definition (messages + system + tools) authored in Google's Gemini format runs on Anthropic Claude, and vice versa, with a thin stateless adapter.
- Tool definitions and tool calls translate both directions (functionDeclarations <-> tools/input_schema; functionCall <-> tool_use; functionResponse <-> tool_result).
- This is the API-layer portability the artifact-layer thesis predicts: the control surface is portable; only the vendor runtime differs.

## What it does NOT do
- It does not reproduce Google's Managed Agents runtime (the managed loop, Linux sandbox, built-in code execution / Google Search). Running a Google managed-agent definition on Claude would require building that harness, not translating a format.