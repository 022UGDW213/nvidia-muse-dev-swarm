# DevSwarm

Thirty specialist workers. One SQLite queue. Atomic claims. Visible results.

DevSwarm is a DevOps agent fleet for the [timeloops](https://o22ugdw213.network) lab — a coordinator plus up to 30 detached workers that pull scoped work from `swarm.db`, ground each task in a Hugging Face–trained FTS index, and write the outcome back where you can inspect it.

[Live showcase](https://o22ugdw213.network/#devswarm) · [Training corpus](https://github.com/022UGDW213/dev-swarm-training) · [Work](https://o22ugdw213.network/portfolio.html)

| | |
|---|---|
| Workers | 30 specialist profiles — `dev-swarm/agents/devops-01.json` … `devops-30.json` |
| Queue | SQLite WAL (`dev-swarm/swarm.db`); a worker claims one pending row with a single `UPDATE … WHERE id=(SELECT … LIMIT 1)` |
| Knowledge | 3,295 docs in the FTS5 index shipped by the companion [`dev-swarm-training`](https://github.com/022UGDW213/dev-swarm-training) repo |
| Skills | 38 runbooks in `dev-swarm/skills/` — 30 DevOps specialties + 8 specialist lanes |
| LLM | NVIDIA hosted OpenAI-compatible endpoint (`moonshotai/kimi-k3`) — requires an `NVIDIA_API_KEY` |

Every count in that table was re-measured on this workstation on **2026-09-26**; the exact commands are listed under [How these numbers were measured](#how-these-numbers-were-measured) at the bottom.

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

Real terminal capture from a 30-worker run on this workstation, 2026-09-26 (worker ids are `devops-NN-<6 hex>`; the middle of the `up -n 30` listing is elided for length):

```text
$ python3 swarm.py up -n 30
  devops-01-ba85c5: Docker Specialist (docker)
  devops-02-f8e8a2: Kubernetes Operator (kubernetes)
  ...
  devops-30-c12595: Service Mesh Engineer (service-mesh)
swarm up: 30 workers starting

$ python3 swarm.py submit shell '{"cmd":"echo devswarm 30-worker run && uname -s && python3 -V","timeout":60}'
2

$ python3 swarm.py wait 2
task #2 [shell] status=done worker=devops-23-08764d attempts=1
payload: {"cmd":"echo devswarm 30-worker run && uname -s && python3 -V","timeout":60}
ok: True  agent: devops-23
--- output ---
devswarm 30-worker run
Linux
Python 3.10.12
```

A failing task is reported just as plainly — this one was submitted in the same session (`pytest` is not installed on this workstation):

```text
task #1 [shell] status=failed worker=devops-20-4f7e49 attempts=1
ok: False  agent: devops-20
--- output ---
/bin/sh: 1: pytest: not found
--- error ---
exit=127
```

## How it works

1. **Intake** — a concrete outcome becomes a work unit (`kind` + JSON payload). Vague requests do not enter the queue.
2. **Coordinate** — a worker claims one pending row with a single statement, `UPDATE tasks SET status='running' … WHERE id = (SELECT id FROM tasks WHERE status='pending' ORDER BY id LIMIT 1)`. SQLite serializes the write, so no two workers get the same task.
3. **Ground** — an FTS5 query on `knowledge/index.db` attaches the top 3 hits as `skill_context`. If that index has not been built yet the lookup returns `[]` silently and the task still runs.
4. **Execute** — `shell` / `fetch` / `python`. Errors return with status, output, and context.
5. **Recover** — claims older than 180 s (`STALE_AFTER`) are requeued by the next worker poll; `down` resets in-flight work to `pending`.

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

## NVIDIA hosted API

The client is `nvidia/client_example.py`: a stdlib-only `urllib` POST to the OpenAI-compatible chat-completions endpoint.

- Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`
- Default model: `moonshotai/kimi-k3` (override with `NVIDIA_MODEL`)
- Auth: `Authorization: Bearer $NVIDIA_API_KEY` — never commit the key

What is verified **now** (2026-09-26): the endpoint is live and auth-gated — a `POST` with no `Authorization` header returns **HTTP 401**, body `Header of type 'authorization' was missing`, in 0.31 s. A `GET`-style reachability check is included in [How these numbers were measured](#how-these-numbers-were-measured).

What is **not** verified now: the free-tier `HTTP 200` completion recorded in `nvidia/MODELS.md` on 2026-09-17. `NVIDIA_API_KEY` is not set on this workstation, so that call cannot be replayed here — treat it as a dated observation, not a current result. `nvidia/nemotron-3-ultra-550b-a55b` is referenced in local config and was never live-tested.

Running the client without a key exits with the message it is designed to give:

```text
$ python3 nvidia/client_example.py
Set NVIDIA_API_KEY first: export NVIDIA_API_KEY='nvapi-...'
```

With a key:

```bash
export NVIDIA_API_KEY="nvapi-..."
python3 nvidia/client_example.py
```

See [`nvidia/MODELS.md`](nvidia/MODELS.md).

## Training corpus

The companion repo [dev-swarm-training](https://github.com/022UGDW213/dev-swarm-training) ships a 3,295-doc FTS5 snapshot plus a zero-dependency Node module. The lane counts below are the module's real output on this workstation (the index holds exactly 3,295 docs, not "3,295+"):

```js
import { searchKnowledge, stats } from 'dev-swarm-training';
stats();
// {
//   total: 3295,
//   lanes: {
//     'llm-ops': 650, 'elearning-tutoring': 588, 'swarm-multiagent': 410,
//     'mcp-protocol': 371, 'devops-01': 300, 'devops-16': 300,
//     'devops-27': 300, 'design-web': 226, 'ml-training': 150
//   }
// }
```

Note: `index.js` declares `engines: { node: ">=23.4" }` for `node:sqlite`. It runs on Node v22.23.2 (this workstation) with an `ExperimentalWarning: SQLite is an experimental feature` on stderr.

Ingest uses the Hugging Face `datasets-server` `/parquet` + `/rows` APIs over `curl` — not `huggingface_hub`.

## Layout

```
nvidia/
  client_example.py     OpenAI-compatible NVIDIA client
  MODELS.md             hosted-API model notes
dev-swarm/
  swarm.py              coordinator CLI + worker loop
  agents/               devops-01.json … devops-30.json
  skills/               38 runbooks (30 DevOps + 8 extra lanes)
  train/                HF ingest → knowledge/ + FTS index
  README.md             specialties × datasets
```

`dev-swarm/swarm.db`, `dev-swarm/logs/` and `dev-swarm/knowledge/` are runtime/derived artifacts created by `up` and `train`; they are gitignored and not part of this repository. The published corpus lives in `dev-swarm-training`.

## Private access (lab)

The public site is GitHub Pages on [o22ugdw213.network](https://o22ugdw213.network). The dashboard and desktop are Cloudflare Tunnel public hostnames; when the tunnel connector is up but the local origin process is down, Cloudflare answers **530** instead of the app. Measured from this workstation on 2026-09-26:

| Host | Result |
|---|---|
| `o22ugdw213.network/` | HTTP 200 |
| `o22ugdw213.network/portfolio.html` | HTTP 200 (redirects to `/portfolio`) |
| `desktop.o22ugdw213.network` | HTTP **530** (no local origin) |
| `dashboard.o22ugdw213.network/Dashboard` | does not resolve in DNS from here |
| `ssh.o22ugdw213.network` | resolves (Cloudflare anycast) |

To publish SSH on the same tunnel:

```yaml
- hostname: ssh.o22ugdw213.network
  service: ssh://localhost:22
```

Gate it with Cloudflare Access, and connect with:

```
Host timeloops
  HostName ssh.o22ugdw213.network
  ProxyCommand cloudflared access ssh --hostname %h
```

Do not open port 22. Put Access in front of the dashboard, desktop and SSH; leave the marketing site public.

## Notes

- Workers do not survive VM replacement — re-run `up` after one.
- No credentials live in this tree; every key reference is a `nvapi-...` placeholder. Rotate any NVIDIA key that was ever pasted in chat.
- `knowledge/` is derived data — re-run `train` to refresh it.

## How these numbers were measured

All on 2026-09-26, from this repository's working tree unless stated otherwise.

| Claim | Measured value | Command |
|---|---|---|
| 30 specialist workers | 30 files, ids `devops-01` … `devops-30`, 30 distinct specialties, all JSON-parse clean | `ls dev-swarm/agents/*.json \| wc -l` + `python3 -c "import json,glob;[json.load(open(f)) for f in glob.glob('dev-swarm/agents/*.json')]"` |
| 30-worker cap | `up -n 31` prints `max 30 workers` and exits 2 (`MAX_WORKERS = 30`) | `python3 swarm.py up -n 31; echo $?` |
| Stale-claim window | `STALE_AFTER = 180` in `swarm.py` | `grep -n 'STALE_AFTER' dev-swarm/swarm.py` |
| Queue is SQLite WAL | `PRAGMA journal_mode` → `wal`; tables `tasks`, `workers` | `cd dev-swarm && python3 -c "import sqlite3;c=sqlite3.connect('swarm.db');print(c.execute('PRAGMA journal_mode').fetchone())"` |
| Live run works | 30 workers up, `#2` done by `devops-23`, `#1` failed exit 127, `down` → 0 workers and `running` → `pending` | transcript above |
| 38 runbooks | 38 `*.md` in `dev-swarm/skills/` | `ls dev-swarm/skills/*.md \| wc -l` |
| 3,295 FTS docs | `SELECT count(*) FROM docs` → 3295 | `cd dev-swarm-training && python3 -c "import sqlite3;print(sqlite3.connect('data/index.db').execute('select count(*) from docs').fetchone())"` |
| Lane breakdown | `stats()` → the object quoted above | `cd dev-swarm-training && node -e "import('./index.js').then(m=>console.log(m.stats()))"` |
| NVIDIA endpoint live + auth-gated | HTTP 401 without a key | `curl -s -o /dev/null -w '%{http_code}\n' -X POST https://integrate.api.nvidia.com/v1/chat/completions -H 'Content-Type: application/json' -d '{"model":"moonshotai/kimi-k3","messages":[{"role":"user","content":"hi"}]}'` |
| No keys committed | only `nvapi-...` placeholders matched | `grep -rInE 'nvapi-|sk-[A-Za-z0-9]{20}\|AKIA[0-9A-Z]{16}\|ghp_' .` |

---

PYTHON 3 · SQLITE TASK QUEUE · 30 WORKERS · ATOMIC CLAIMS
