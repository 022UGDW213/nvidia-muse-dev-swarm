# nvidia-muse-dev-swarm

Built in one session with **Muse** (Meta's personal AI agent) on September 17, 2026:
a 30-agent DevOps swarm whose skill knowledge is trained from Hugging Face
datasets — powered by **NVIDIA's free-tier API**, verified live with
`moonshotai/kimi-k3`.

## What this is

- **`nvidia/`** — everything learned about NVIDIA's free-tier
  (`https://integrate.api.nvidia.com/v1/chat/completions`): a drop-in
  OpenAI-compatible client example and notes on the free-tier models tested.
- **`dev-swarm/`** — a DevOps agent swarm: a coordinator + up to 30 detached
  worker agents sharing a sqlite task queue. Each worker loads one of 30
  specialist profiles (docker, kubernetes, terraform, ansible, …) and consults
  a local knowledge index built from real Hugging Face datasets before
  executing tasks.

## NVIDIA free tier — verified working (2026-09-17)

- Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`
  (OpenAI-compatible, streaming supported).
- Test: `moonshotai/kimi-k3` with `reasoning_effort: max`, vision input
  (`image_url`), streaming — **HTTP 200**, full reasoning + answer returned.
- Config also references `nvidia/nemotron-3-ultra-550b-a55b`.
- Auth: `Authorization: Bearer $NVIDIA_API_KEY`. Never hardcode the key —
  see `nvidia/client_example.py`. Rotate any key that was ever pasted in chat.

```bash
export NVIDIA_API_KEY="nvapi-..."
python3 nvidia/client_example.py
```

## Dev swarm — quickstart

```bash
cd dev-swarm
python3 swarm.py train            # ingest HF dataset samples for all 30 agents, build FTS index
python3 swarm.py up -n 30         # start all 30 workers (worker i -> devops-(i+1) profile)
python3 swarm.py status           # workers + queue depth
python3 swarm.py submit shell '{"cmd": "docker ps", "timeout": 30}'
python3 swarm.py down             # stop all workers
```

### How the "training" works

`train/ingest.py` maps each of the 30 specialties to 1–2 real Hugging Face
datasets (verified live via the datasets-server `/parquet` + `/rows` APIs —
plain `curl`, no `huggingface_hub`, which breaks behind some proxies). It pulls
a few hundred rows per dataset into `knowledge/<agent>.jsonl` and builds a
shared FTS5 index (`knowledge/index.db`). When a worker claims a task, it runs
a keyword FTS lookup and attaches the top 3 hits as `skill_context` in the
task result — lightweight skill grounding, no GPU needed.

See [`dev-swarm/README.md`](dev-swarm/README.md) for the full 30-specialty ×
dataset mapping and architecture details.

## Repo layout

```
nvidia/
  client_example.py   # OpenAI-compatible NVIDIA client (env-var key, streaming)
  MODELS.md           # free-tier model notes
dev-swarm/
  swarm.py            # coordinator CLI + workers (sqlite queue)
  agents/             # 30 profiles: devops-01.json … devops-30.json
  skills/             # 30 DevOps runbooks, one per specialty
  train/
    ingest.py         # HF dataset ingest -> knowledge/ + FTS index
    generate.py       # regenerates profiles + runbooks from one data table
  README.md
```

## Notes

- Workers don't survive VM replacement — re-run `up` after one.
- No credentials are stored anywhere in this repo.
- Built with Muse. Iterated fast, verified live.
