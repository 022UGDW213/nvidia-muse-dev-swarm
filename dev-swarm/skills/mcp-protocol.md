# MCP Protocol Skill

Runbook for Model Context Protocol work. Grounded in 371 HF docs:
`hf-mcp-server/test-mcp-logs` (113 real session logs),
`kshitijthakkar/mcp-server-bench` (150 load-test results),
`DeepNLP/mcp-servers` (108 server catalog entries).

## The handshake (from real session logs)

Every MCP session starts with `initialize`:

```json
{"protocolVersion": "2025-06-18",
 "capabilities": {"sampling": {}, "elicitation": {}},
 "clientInfo": {"name": "fast-agent-mcp", "version": "0.3.28"}}
```

- **protocolVersion is negotiated.** Log it; mismatches are the first thing to
  check when a client/server pair misbehaves.
- **Capabilities are explicit:** `sampling` (server may ask the client LLM for
  completions), `elicitation` (server may request user input). A server must
  not assume either — declare and check.
- Sessions end with `session_delete`. If you see orphaned sessions, the client
  isn't cleaning up — the #1 hygiene bug in the log corpus.

## Auth

The logs carry an `authorized` boolean per session — 58/113 test sessions were
**unauthorized**. Design for this:

- Gate tool execution on the auth check, not on session creation. An
  unauthorized session can still handshake; it must not execute.
- Log auth failures with client name + IP (`::ffff:127.0.0.1` style) — the
  corpus shows this is how abuse gets spotted.

## What's in the ecosystem (catalog, 108 servers)

MCP servers span: dev tools, data sources, AI model gateways, automation.
When evaluating a server for Juan's "juan-vm" MCP server or n8n wiring:

1. Check its declared tools and required capabilities.
2. Check its transport: the bench corpus covers `http_api` (90 scenarios) and
   `mcp_streamable` (60) — stdio suits local (like juan-vm), streamable HTTP
   suits remote.
3. Load-test before trusting: the bench runs virtual users against tools
   (echo, etc.) on `gradio` and `fastmcp` servers and records success rate,
   req/s, avg/p95/p99 latency.

## Load-test checklist (from mcp-server-bench)

Per scenario record: `scenario_id`, server, protocol, tool, `virtual_users`,
`duration_s`, `total_requests`, `successful_requests`, `failed_requests`,
`requests_per_second`, `avg_latency_ms`, `p95_latency_ms`, `p99_latency_ms`.

- **p95/p99, not avg:** MCP tool calls have long-tail latency (LLM-backed
  tools especially). Size timeouts off p99.
- **Failure budget:** any `failed_requests > 0` at 1 virtual user means the
  server is broken, not loaded — fix before scaling users.
- **Concurrency limits:** some servers set `concurrency_limit`; respect it or
  you'll benchmark the queue, not the server.

## juan-vm mapping (Juan's local MCP server)

His server (`~/workspace/mcp-server/server.py`, stdio) exposes:
`open_chrome`, `apt_install`, `bash` (root), `vm_status`. When adding tools:

- One tool = one verb, JSON-schema params with `required` — same discipline
  as the LLM tool-calling skill.
- `bash` with root is the dangerous one: scope commands, log invocations,
  never expose it over the network without the auth lesson above.
- Keep the skill doc (`~/workspace/skills/mcp-server/SKILL.md`) in sync with
  the tool list — drift between docs and tools is how agents call tools that
  don't exist.

## Pitfalls

- **Version drift:** client 0.3.28 vs server expecting another protocolVersion
  → silent capability mismatch. Pin and log versions on both ends.
- **Elicitation without UX:** if your server uses elicitation, the client must
  have a human in the loop — headless clients hang.
- **Sampling loops:** server asks client LLM → client calls server tool →
  server asks again. Cap recursion depth.
- **Test logs are synthetic:** 113 sessions from one test harness — great for
  protocol shape, not for real-world traffic patterns. Validate against your
  own logs before tuning timeouts.
