# NVIDIA free-tier model notes (observed 2026-09-17)

Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`
(OpenAI-compatible; streaming supported via `Accept: text/event-stream`.)

## Observed live on 2026-09-17

- **`moonshotai/kimi-k3`** — vision + chat, `reasoning_effort: max`,
  `max_tokens: 16384`, temperature 1, seed 0. Streaming returned
  `reasoning_content` deltas followed by `content` deltas, `finish_reason:
  "stop"`, and a usage block. **HTTP 200** at that time.
  Example vision input (still live, HTTP 200 `image/jpeg` 183,601 bytes):
  `https://assets.ngc.nvidia.com/products/api-catalog/phi-3-5-vision/example1b.jpg`

This is a dated observation, not a current result. Re-checked on 2026-09-26 from
this workstation: `NVIDIA_API_KEY` was **not set**, so the completion could not
be replayed. The endpoint itself is live and enforces auth — an unauthenticated
`POST` returns:

```text
HTTP 401 — "Header of type `authorization` was missing"   (0.31 s)
```

The model id and the free-tier status therefore remain **unverified as of
2026-09-26**; re-run `nvidia/client_example.py` with a key to confirm them.

## Referenced in local config (not live-tested here)

- **`nvidia/nemotron-3-ultra-550b-a55b`** — present in the iBot stack config at
  `cluster-config/nvidia-nemotron-config.json` (fields `name` and
  `model_name`, verified 2026-09-26); that config expects `NVIDIA_API_KEY`.

## Auth

- Header: `Authorization: Bearer $NVIDIA_API_KEY`
- Get a key at https://build.nvidia.com (free tier available).
- If a key was ever pasted into chat or a shell command, rotate it and store
  the replacement in a secure vault / connector — never in code or chat.
