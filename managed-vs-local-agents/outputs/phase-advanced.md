# Advanced primitives: firsthand retest

Tested against the live Gemini API Managed Agents dev endpoint (generativelanguage.googleapis.com/v1beta), 2026-06-01.

| Primitive | Result | Detail |
|-----------|--------|--------|
| Custom SKILL.md | PASS | answer=True, skill_applied(HAIKU)=True; output='6 multiplied by 7 is 42.

HAIKU:
Six and seven meet
Forty-two is their product
Numbers are aligned' |
| Secrets via egress proxy | FAIL-run | run None: TimeoutError: The read operation timed out |
| tools[] incl. mcp_server (dev endpoint) | REJECTED | dev endpoint 400: {"error":{"message":"The value 'mcp_server' is not supported for 'type' at 'tools[3]'. Supported values: 'google_search', 'url_context', 'code_execution'.","code":"invalid_request"}} (may be Enterprise/Vertex-only) |
| Subagents | NOT-EXPOSED | step types observed: ['code_execution_call', 'code_execution_result', 'model_output', 'thought']; no sub-agent/agent-spawn step type present |