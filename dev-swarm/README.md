# Dev Swarm — 30 DevOps workers, HF-trained skills

Coordinator plus up to 30 detached workers on a shared SQLite queue. Each worker loads `agents/devops-NN.json` at start and consults `knowledge/index.db` (FTS5) before running a task.

Showcase: [o22ugdw213.network](https://o22ugdw213.network/#devswarm)  
Training snapshot: [dev-swarm-training](https://github.com/022UGDW213/dev-swarm-training) (3,295 docs)

Counts on this page were re-measured in this working tree on 2026-09-26 (`ls dev-swarm/agents/*.json | wc -l` → 30; `ls dev-swarm/skills/*.md | wc -l` → 38).

## Layout

```
dev-swarm/
  swarm.py            coordinator CLI + worker_main
  agents/             devops-01.json … devops-30.json  (30 files)
                      (id, name, specialty, skills[], hf_datasets[], description)
  skills/             runbooks — 38 files: one per specialty + 8 extra lanes
  train/
    ingest.py         HF sample ingest → knowledge/<agent>.jsonl + FTS index
    generate.py       regenerates agents/ + the 30 specialty runbooks
    ingest_*.py       lane-specific ingest (ml, tutoring, music, design, muse sdk)
  README.md           this file
```

Generated at runtime (not in the repository — see `.gitignore`):

```
  knowledge/          <agent>.jsonl samples, index.db, manifest.json
  logs/               per-worker logs
  swarm.db            tasks + workers (WAL)
```

## The 30 specialists

docker · kubernetes · helm · terraform · ansible · pulumi · github-actions · gitlab-ci · jenkins · argocd · prometheus · grafana · elk-logging · linux-admin · bash-scripting · python-automation · networking · nginx · postgres · redis · kafka · vault-secrets · aws · gcp · azure · security-hardening · incident-response · backup-dr · load-testing · service-mesh

Each `agents/devops-NN.json` carries `id`, `name`, `specialty`, `skills[]` and `hf_datasets[]`. Across the 30 profiles there are 30 distinct specialties and 14 distinct Hugging Face datasets.

## Queue semantics (`swarm.py`)

| Constant / column | Behavior |
|---|---|
| `MAX_WORKERS = 30` | hard cap on `up -n` — `up -n 31` prints `max 30 workers` and exits 2 |
| `STALE_AFTER = 180` | running claims older than 180s are requeued by the next poll |
| `tasks.attempts` | incremented on each claim |
| claim SQL | one pending row, one worker, one statement: `UPDATE tasks SET status='running', … WHERE id = (SELECT id FROM tasks WHERE status='pending' ORDER BY id LIMIT 1)` |
| `down` | SIGTERM by PID, clear `workers`, reset `running` → `pending` |

`PRAGMA journal_mode=WAL` is set in `db()`, so the database is WAL-mode (verified: `PRAGMA journal_mode` → `wal`).

Task kinds: `shell` · `fetch` · `python`.

CLI: `up` `down` `train` `submit` `status` `result` `results` `wait` `worker`.

## Train

Pulls rows per mapped dataset via datasets-server `/rows` (curl only — never `huggingface_hub`; default `--rows 200`).

```bash
cd dev-swarm
python3 swarm.py train                                  # all 30 agents
python3 swarm.py train --agents devops-01,devops-16     # subset
python3 swarm.py train --agents devops-01 --rows 100    # smaller sample
```

`ingest.py` writes `knowledge/<agent>.jsonl`, records per-dataset status in `knowledge/manifest.json`, then rebuilds `knowledge/index.db` from **all** `knowledge/*.jsonl` (`CREATE VIRTUAL TABLE docs USING fts5(agent_id, dataset, text)`).

Dataset substitutions (verified 2026-09-17): `bigcode/the-stack-smol` (401),
`codeparrot/github-code-clean` (/rows job killed), `jtatman/...` (401),
`Salesforce/xlam-function-calling-60k` (401), `nvidia/OpenCodeInstruct`
(/rows config mismatch), `neulab/conala` (/rows 404), `openai_humaneval` (404)
were replaced with served code/instruction datasets. That list is a dated record of what the datasets-server returned on 2026-09-17; it was not replayed.

A `train` run on this workstation was interrupted part-way and the `knowledge/` directory it left behind is **not** committed: 20 `<agent>.jsonl` files existed, only `devops-01` … `devops-08` held data (400 docs each = 3,200 docs) and `devops-09` … `devops-20` were empty; no `index.db` and no `manifest.json` were produced. `knowledge/` is gitignored — re-run `train` for a complete index, or use the published 3,295-doc snapshot in `dev-swarm-training`.

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
When `knowledge/index.db` is absent the lookup returns `[]` and the task runs ungrounded; the SQL path itself was exercised against the published index (schema `fts5(agent_id, dataset, text)`) and returned 3 hits per query.

## Extra training lanes

| Lane | Runbook | Ingest | Docs in the published index |
|---|---|---|---|
| `ml-training` | `skills/ml-training.md` | `train/ingest_ml_agents.py` | 150 |
| `llm-ops` | `skills/llm-ops.md` | `train/ingest_ml_agents.py` | 650 |
| `swarm-orchestration` | `skills/swarm-orchestration.md` | `train/ingest_ml_agents.py` | 410 (`swarm-multiagent` lane id) |
| `mcp-protocol` | `skills/mcp-protocol.md` | `train/ingest_ml_agents.py` | 371 |
| `ai-tutoring` | `skills/ai-tutoring.md` | `train/ingest_tutoring.py` | 588 (`elearning-tutoring` lane id) |
| `music-production` | `skills/music-production.md` | `train/ingest_music.py` | — not in the published snapshot |
| `ui-ux-design` | `skills/ui-ux-design.md` | `train/ingest_design.py` | 226 (`design-web` lane id) |
| `muse-code-sdk` | `skills/muse-code-sdk.md` | `train/ingest_muse_sdk.py` | — not in the published snapshot |

Counts are `SELECT agent_id, COUNT(*) FROM docs GROUP BY agent_id` over `dev-swarm-training/data/index.db` (total 3,295). The published snapshot also carries `devops-01`, `devops-16` and `devops-27` at 300 docs each.

The published index snapshot (3,295 docs) lives in [dev-swarm-training](https://github.com/022UGDW213/dev-swarm-training).

## Operator access

Dashboard / desktop tunnels are Cloudflare Tunnel public hostnames. HTTP **530** means the connector is up and the origin process is not. Measured from this workstation on 2026-09-26: `desktop.o22ugdw213.network` → **530**; `dashboard.o22ugdw213.network` → no DNS record resolvable from here. Publish SSH on the same tunnel:

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
- No API keys in this tree — verified by scanning for `nvapi-` / `sk-` / `AKIA` / `ghp_` patterns; only `nvapi-...` placeholders match.
- `knowledge/` is derived — re-run `train` to refresh it.
