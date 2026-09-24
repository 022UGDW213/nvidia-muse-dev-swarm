# DevSwarm

Thirty specialist workers. One SQLite queue. Atomic claims. Visible results.

DevSwarm is a DevOps agent fleet for the [timeloops](https://o22ugdw213.network) lab — a coordinator plus up to 30 detached workers that pull scoped work from `swarm.db`, ground each task in a Hugging Face–trained FTS index, and write the outcome back where you can inspect it.

[Live showcase](https://o22ugdw213.network/#devswarm) · [Training corpus](https://github.com/022UGDW213/dev-swarm-training) · [Work](https://o22ugdw213.network/portfolio.html)

| | |
|---|---|
| Workers | 30 specialists (`devops-01` … `devops-30`) |
| Queue | SQLite WAL, one claim per task in a single transaction |
| Knowledge | 3,295+ FTS-indexed docs across ML, LLM, swarm, MCP, tutoring |
| Skills | 30 DevOps runbooks + specialist lanes (LLM ops, MCP, music, UI/UX, …) |
| LLM | NVIDIA free-tier API (`moonshotai/kimi-k3`, OpenAI-compatible) |

A swarm should make the work more visible — not hide it behind magic.

## Quickstart

```bash
cd dev-swarm
python3 swarm.py train            # ingest HF samples, build knowledge/index.db
python3 swarm.py up -n 30         # worker i → devops-(i+1)
python3 swarm.py status           # alive workers, queue depth, recent tasks
python3 swarm.py submit shell '{"cmd":"pytest -q","timeout":300}'
python3 swarm.py wait 1           # block until done / failed
python3 swarm.py result 1
python3 swarm.py down             # SIGTERM via PID table — no pkill
```

Task kinds: `shell` · `fetch` · `python`.

```text
$ python3 swarm.py up -n 30
✓ 30 specialist workers online  sqlite://swarm.db

$ python3 swarm.py submit shell '{"cmd":"pytest -q","timeout":300}'
task #42 queued → claimed by devops-07

$ python3 swarm.py wait 42
✓ task #42 [shell] done  attempts=1
```

## How it works

1. **Intake** — a concrete outcome becomes a work unit (`kind` + JSON payload). Vague requests do not enter the queue.
2. **Coordinate** — a worker claims one pending row in a single `UPDATE … WHERE id=(SELECT … LIMIT 1)` transaction. No duplicate effort.
3. **Ground** — FTS lookup on `knowledge/index.db` attaches the top 3 hits as `skill_context`.
4. **Execute** — `shell` / `fetch` / `python`. Errors return with status, output, and context.
5. **Recover** — claims older than 180s are treated as stale and requeued. `down` resets in-flight work to `pending`.

```
         submit()
            |
            v
     +-- swarm.db --+     knowledge/index.db (FTS5)
     | tasks/workers |            |
     +---------------+            |
            |  atomic claim       | skill_context
     +----------------------------+
     |  30 detached workers
     |  devops-01 … devops-30
     +-- result JSON (ok / output / error)
```

## The 30 specialists

docker · kubernetes · helm · terraform · ansible · pulumi · github-actions · gitlab-ci · jenkins · argocd · prometheus · grafana · elk-logging · linux-admin · bash-scripting · python-automation · networking · nginx · postgres · redis · kafka · vault-secrets · aws · gcp · azure · security-hardening · incident-response · backup-dr · load-testing · service-mesh

Extra training lanes (runbooks in `dev-swarm/skills/`): `ml-training` · `llm-ops` · `swarm-orchestration` · `mcp-protocol` · `ai-tutoring` · `music-production` · `ui-ux-design` · `muse-code-sdk`.

Full dataset map and ingest notes: [`dev-swarm/README.md`](dev-swarm/README.md).

## NVIDIA free tier

OpenAI-compatible chat completions, verified 2026-09-17.

- Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`
- Model tested: `moonshotai/kimi-k3` (`reasoning_effort: max`, vision, streaming) — HTTP 200
- Also referenced: `nvidia/nemotron-3-ultra-550b-a55b`
- Auth: `Authorization: Bearer $NVIDIA_API_KEY` — never commit the key

```bash
export NVIDIA_API_KEY="nvapi-..."
python3 nvidia/client_example.py
```

See [`nvidia/MODELS.md`](nvidia/MODELS.md).

## Training corpus

The companion repo [dev-swarm-training](https://github.com/022UGDW213/dev-swarm-training) ships a 3,295-doc FTS5 snapshot plus a zero-dependency Node module:

```js
import { searchKnowledge, stats } from 'dev-swarm-training';
stats();
// { total: 3295, lanes: { 'ml-training': 150, 'llm-ops': 650, ... } }
```

Ingest uses the Hugging Face `datasets-server` `/parquet` + `/rows` APIs over `curl` — not `huggingface_hub`.

## Layout

```
nvidia/
  client_example.py     OpenAI-compatible NVIDIA client
  MODELS.md             free-tier model notes
dev-swarm/
  swarm.py              coordinator CLI + worker loop
  agents/               devops-01.json … devops-30.json
  skills/               runbooks (DevOps + extra lanes)
  train/                HF ingest → knowledge/ + FTS index
  README.md             specialties × datasets
```

## Private access (lab)

The public site is GitHub Pages on [o22ugdw213.network](https://o22ugdw213.network). The live dashboard and desktop are Cloudflare Tunnel origins; they return **530** when `cloudflared` is up but the local process is down. Operator path:

- Dashboard: `https://dashboard.o22ugdw213.network/Dashboard`
- Desktop: `https://desktop.o22ugdw213.network` (Kasm / VNC)
- SSH: publish `ssh://localhost:22` on the same tunnel (`ssh.o22ugdw213.network`) and gate it with Cloudflare Access — `cloudflared access ssh --hostname ssh.o22ugdw213.network`

Do not open port 22. Put Access in front of dashboard, desktop, and SSH; leave the marketing site public.

## Notes

- Workers do not survive VM replacement — re-run `up` after one.
- No credentials live in this tree. Rotate any NVIDIA key that was ever pasted in chat.
- `knowledge/` is derived data — re-run `train` to refresh it.
- Built with Muse, 2026-09-17. Iterated against a live NVIDIA endpoint.

---

PYTHON 3 · SQLITE TASK QUEUE · 30 WORKERS · ATOMIC CLAIMS
