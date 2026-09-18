# Dev Swarm — 30 DevOps agent workers with HF-trained skill knowledge

A DevOps agent swarm for this VM: a coordinator plus up to 30 detached worker
agents that pull tasks from a shared sqlite queue. Each worker loads a
specialist profile (`agents/devops-NN.json`) at startup and consults a shared
FTS knowledge index (`knowledge/index.db`) built from real Hugging Face
dataset samples before running each task.

Adapted from `~/workspace/agent-swarm/swarm.py` (same queue/worker mechanics,
PID-tracked shutdown — no `pkill`).

## Layout

```
dev-swarm/
  swarm.py            coordinator CLI
  agents/             30 agent profiles: devops-01.json … devops-30.json
                      (id, name, specialty, skills[], hf_datasets[], description)
  skills/             30 runbooks, one per specialty (<40 lines each)
  train/
    ingest.py         HF sample ingest -> knowledge/<agent>.jsonl + FTS index
    generate.py       regenerates agents/ + skills/ from the data table
  knowledge/          <agent>.jsonl samples, index.db (FTS5), manifest.json
  logs/               per-worker logs
  swarm.db            task queue + worker registry (sqlite)
```

## The 30 specialists

docker · kubernetes · helm · terraform · ansible · pulumi · github-actions ·
gitlab-ci · jenkins · argocd · prometheus · grafana · elk-logging · linux-admin ·
bash-scripting · python-automation · networking · nginx · postgres · redis ·
kafka · vault-secrets · aws · gcp · azure · security-hardening ·
incident-response · backup-dr · load-testing · service-mesh

## Train (ingest HF samples)

Pulls ~200 rows per mapped dataset via the datasets-server `/rows` API
(verified 2026-09-17; curl only — never `huggingface_hub`), converts to JSONL,
and builds the FTS index. A few MB total.

```bash
cd ~/workspace/dev-swarm
python3 swarm.py train                                  # all 30 agents
python3 swarm.py train --agents devops-01,devops-16     # subset
python3 swarm.py train --agents devops-01 --rows 100    # smaller sample
```

Dataset substitutions (verified 2026-09-17): `bigcode/the-stack-smol` (401),
`codeparrot/github-code-clean` (/rows job killed), `jtatman/...` (401),
`Salesforce/xlam-function-calling-60k` (401), `nvidia/OpenCodeInstruct`
(/rows config mismatch), `neulab/conala` (/rows 404), `openai_humaneval` (404)
were replaced with verified code/instruction datasets. Per-dataset status is in
`knowledge/manifest.json`.

## Run the swarm

```bash
cd ~/workspace/dev-swarm
python3 swarm.py up -n 30      # start all 30 (worker i -> devops-(i+1) profile)
python3 swarm.py status        # workers, queue depth, recent tasks
python3 swarm.py down          # stop all workers (SIGTERM via PID table)
```

## Submit tasks

```bash
python3 swarm.py submit shell  '{"cmd": "docker ps", "timeout": 30}'
python3 swarm.py submit fetch  '{"url": "https://example.com", "out": "/tmp/x.html"}'
python3 swarm.py submit python '{"code": "print(2+2)"}'
python3 swarm.py wait 1 --timeout 120
python3 swarm.py result 1
python3 swarm.py results -n 10
```

When a worker claims a task it runs a lightweight FTS query over the knowledge
index using keywords from the payload and attaches the top 3 hits as
`skill_context` in the task result (visible in `result` output and the worker
log). No heavyweight RAG — just FTS text.

## Training lanes (added after the initial 30 DevOps agents)

Specialist lanes, each with a runbook in `skills/<lane>.md` and an ingest
script in `train/ingest_<lane>.py` that pulls ~150–200 HF rows per mapped
dataset (curl via the datasets-server `/parquet` API — never `huggingface_hub`,
which can't parse the egress proxy URL):

- `ml-training` — ML training workflows (ingest_ml_agents.py)
- `llm-ops` — LLM deployment/serving ops (ingest_ml_agents.py)
- `swarm-multiagent` — multi-agent orchestration (ingest_ml_agents.py)
- `mcp-protocol` — MCP server protocol (ingest_ml_agents.py)
- `ai-tutoring` — e-learning tutoring (ingest_tutoring.py)
- `music-production` — electronic music composition (ingest_music.py)
- `ui-ux-design` — web design patterns (ingest_design.py)
- `muse-code-sdk` — Meta's Muse Code SDK / agentic coding (ingest_muse_sdk.py)

## Notes

- Workers do not survive VM replacement; re-run `up` after one.
- No API keys or credentials are stored anywhere in this tree.
- `knowledge/` is derived data — re-run `train` to refresh it.
