# Dev Swarm — 30 DevOps workers, HF-trained skills

Coordinator plus up to 30 detached workers on a shared SQLite queue. Each worker loads `agents/devops-NN.json` at start and consults `knowledge/index.db` (FTS5) before running a task.

Showcase: [o22ugdw213.network](https://o22ugdw213.network/#devswarm)  
Training snapshot: [dev-swarm-training](https://github.com/022UGDW213/dev-swarm-training) (3,295 docs)

Adapted from `~/workspace/agent-swarm/swarm.py` (same queue/worker mechanics, PID-tracked shutdown — no `pkill`).

## Layout

```
dev-swarm/
  swarm.py            coordinator CLI + worker_main
  agents/             devops-01.json … devops-30.json
                      (id, name, specialty, skills[], hf_datasets[], description)
  skills/             runbooks, one per specialty + extra lanes
  train/
    ingest.py         HF sample ingest → knowledge/<agent>.jsonl + FTS index
    generate.py       regenerates agents/ + skills/ from the data table
    ingest_*.py       lane-specific ingest (ml, tutoring, music, design, muse sdk)
  knowledge/          jsonl samples, index.db, manifest.json
  logs/               per-worker logs
  swarm.db            tasks + workers (WAL)
```

## The 30 specialists

docker · kubernetes · helm · terraform · ansible · pulumi · github-actions · gitlab-ci · jenkins · argocd · prometheus · grafana · elk-logging · linux-admin · bash-scripting · python-automation · networking · nginx · postgres · redis · kafka · vault-secrets · aws · gcp · azure · security-hardening · incident-response · backup-dr · load-testing · service-mesh

## Queue semantics (`swarm.py`)

| Constant / column | Behavior |
|---|---|
| `MAX_WORKERS = 30` | hard cap on `up -n` |
| `STALE_AFTER = 180` | running claims older than 180s are requeued |
| `tasks.attempts` | incremented on each claim |
| claim SQL | one pending row, one worker, one transaction |
| `down` | SIGTERM by PID, clear `workers`, reset `running` → `pending` |

Task kinds: `shell` · `fetch` · `python`.

CLI: `up` `down` `train` `submit` `status` `result` `results` `wait` `worker`.

## Train

Pulls ~200 rows per mapped dataset via datasets-server `/rows` (curl only — never `huggingface_hub`).

```bash
cd dev-swarm
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

## Run

```bash
python3 swarm.py up -n 30      # worker i → devops-(i+1)
python3 swarm.py status
python3 swarm.py submit shell  '{"cmd": "docker ps", "timeout": 30}'
python3 swarm.py submit fetch  '{"url": "https://example.com", "out": "/tmp/x.html"}'
python3 swarm.py submit python '{"code": "print(2+2)"}'
python3 swarm.py wait 1 --timeout 120
python3 swarm.py result 1
python3 swarm.py results -n 10
python3 swarm.py down
```

On claim, the worker runs a keyword FTS query and attaches the top 3 hits as
`skill_context` (shown in `result` and the worker log). Lightweight grounding — no GPU RAG.

## Extra training lanes

| Lane | Runbook | Ingest |
|---|---|---|
| `ml-training` | `skills/ml-training.md` | `train/ingest_ml_agents.py` |
| `llm-ops` | `skills/llm-ops.md` | `train/ingest_ml_agents.py` |
| `swarm-orchestration` | `skills/swarm-orchestration.md` | `train/ingest_ml_agents.py` |
| `mcp-protocol` | `skills/mcp-protocol.md` | `train/ingest_ml_agents.py` |
| `ai-tutoring` | `skills/ai-tutoring.md` | `train/ingest_tutoring.py` |
| `music-production` | `skills/music-production.md` | `train/ingest_music.py` |
| `ui-ux-design` | `skills/ui-ux-design.md` | `train/ingest_design.py` |
| `muse-code-sdk` | `skills/muse-code-sdk.md` | `train/ingest_muse_sdk.py` |

The published index snapshot (3,295 docs) lives in [dev-swarm-training](https://github.com/022UGDW213/dev-swarm-training).

## Operator access

Dashboard / desktop tunnels (`dashboard.o22ugdw213.network`, `desktop.o22ugdw213.network`) are Cloudflare Tunnel public hostnames. HTTP **530** means the connector is up and the origin process is not. Publish SSH on the same tunnel:

```yaml
- hostname: ssh.o22ugdw213.network
  service: ssh://localhost:22
```

Gate it with Cloudflare Access. Client:

```
Host timeloops
  HostName ssh.o22ugdw213.network
  ProxyCommand cloudflared access ssh --hostname %h
```

Do not expose port 22. Access Allow/Block only if you want browser-rendered SSH.

## Notes

- Workers do not survive VM replacement; re-run `up` after one.
- No API keys in this tree.
- `knowledge/` is derived — re-run `train` to refresh it.
