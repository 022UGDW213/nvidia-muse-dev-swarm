# NVIDIA free-tier model notes (observed 2026-09-17)

Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`
(OpenAI-compatible; streaming supported via `Accept: text/event-stream`.)

## Tested live

- **`moonshotai/kimi-k3`** — vision + chat, `reasoning_effort: max`,
  `max_tokens: 16384`, temperature 1, seed 0. Streaming returned
  `reasoning_content` deltas followed by `content` deltas, `finish_reason:
  "stop"`, and a usage block. **HTTP 200 — works on the free tier.**
  Example vision input:
  `https://assets.ngc.nvidia.com/products/api-catalog/phi-3-5-vision/example1b.jpg`

## Referenced in local config (not yet live-tested)

- **`nvidia/nemotron-3-ultra-550b-a55b`** — present in existing model config
  (`~/workspace/ibot/cluster-config/` expects `NVIDIA_API_KEY`).

## Auth

- Header: `Authorization: Bearer $NVIDIA_API_KEY`
- Get a key at https://build.nvidia.com (free tier available).
- If a key was ever pasted into chat or a shell command, rotate it and store
  the replacement in a secure vault / connector — never in code or chat.
