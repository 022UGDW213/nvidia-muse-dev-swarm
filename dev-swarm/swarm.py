#!/usr/bin/env python3
"""DevOps agent swarm: a coordinator + up to 30 specialized worker agents
pulling tasks from a shared sqlite queue. Each worker loads an agent profile
from agents/devops-NN.json at startup (id, name, specialty, skills,
hf_datasets) and consults the shared FTS knowledge index before running a
task, so specialty knowledge informs every job.

Usage:
  swarm.py up [-n 4]                 start the swarm (max 30 workers)
  swarm.py down                      stop all workers
  swarm.py train [--agents all|devops-01,devops-02] [--rows 200]
                                     ingest HF dataset samples -> knowledge/
  swarm.py submit shell '{"cmd": "echo hi", "timeout": 30}'
  swarm.py submit fetch '{"url": "https://example.com", "out": "/tmp/x.html"}'
  swarm.py submit python '{"code": "print(2+2)"}'
  swarm.py status                     workers, queue depth, recent tasks
  swarm.py result <id>                show one task result
  swarm.py results [-n 10]            recent results
  swarm.py wait <id> [--timeout 120]  block until task finishes
"""
import argparse, json, os, re, signal, sqlite3, subprocess, sys, time, uuid

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "swarm.db")
LOGDIR = os.path.join(BASE, "logs")
AGENTSDIR = os.path.join(BASE, "agents")
INDEXDB = os.path.join(BASE, "knowledge", "index.db")
STALE_AFTER = 180  # seconds before a running task is requeued
MAX_WORKERS = 30
STOPWORDS = set("""a an the and or of to in on for with is are was were be been
being it its this that these those as at by from into over after before between
you your we they them he she his her our their not no do does did will would
can could should have has had how what when where which who whom whose why if
then than so such only also just more most other some any all each every per
via using use used make made into out up down about into""".split())


def db():
    os.makedirs(LOGDIR, exist_ok=True)
    c = sqlite3.connect(DB, timeout=30)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL,
        payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
        worker TEXT, attempts INTEGER DEFAULT 0, result TEXT,
        created_at REAL, started_at REAL, finished_at REAL, claimed_at REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS workers (
        id TEXT PRIMARY KEY, pid INTEGER, agent_id TEXT,
        last_heartbeat REAL, started_at REAL)""")
    # migrate older schema without agent_id
    cols = [r[1] for r in c.execute("PRAGMA table_info(workers)")]
    if "agent_id" not in cols:
        c.execute("ALTER TABLE workers ADD COLUMN agent_id TEXT")
    return c


def agent_for_index(i):
    """Worker slot i (0-based) -> agent profile id, cycling over 30."""
    aid = f"devops-{(i % MAX_WORKERS) + 1:02d}"
    p = os.path.join(AGENTSDIR, f"{aid}.json")
    if os.path.exists(p):
        return aid, json.load(open(p))
    return aid, {"id": aid, "name": aid, "specialty": "general",
                 "skills": [], "description": "fallback profile"}


# ---------------- coordinator / CLI ----------------

def cmd_up(n):
    if n > MAX_WORKERS:
        print(f"max {MAX_WORKERS} workers", file=sys.stderr)
        sys.exit(2)
    c = db()
    alive = live_workers(c)
    if alive:
        print(f"swarm already up with {len(alive)} workers; use 'down' first to restart")
        return
    c.execute("UPDATE tasks SET status='pending', worker=NULL WHERE status='running'")
    c.commit()
    for i in range(n):
        aid, prof = agent_for_index(i)
        wid = f"{aid}-{uuid.uuid4().hex[:6]}"
        log = open(os.path.join(LOGDIR, f"{wid}.log"), "a")
        subprocess.Popen([sys.executable, os.path.join(BASE, "swarm.py"),
                          "worker", "--id", wid, "--agent", aid],
                         stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                         start_new_session=True, cwd=BASE)
        c.execute("INSERT OR REPLACE INTO workers VALUES (?,?,?,?,?)",
                  (wid, None, aid, time.time(), time.time()))
        print(f"  {wid}: {prof['name']} ({prof['specialty']})")
    c.commit()
    print(f"swarm up: {n} workers starting")


def live_workers(c):
    rows = c.execute("SELECT id, pid, last_heartbeat FROM workers").fetchall()
    live = []
    for wid, pid, hb in rows:
        ok = pid and _pid_alive(pid)
        if not ok and time.time() - (hb or 0) < 45:
            ok = True  # starting up, hasn't written pid yet
        if ok:
            live.append(wid)
    return live


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def cmd_down():
    c = db()
    for wid, pid, _ in c.execute("SELECT id, pid, last_heartbeat FROM workers").fetchall():
        if pid and _pid_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    c.execute("DELETE FROM workers")
    c.execute("UPDATE tasks SET status='pending', worker=NULL WHERE status='running'")
    c.commit()
    print("swarm down")


def cmd_train(agents, rows):
    script = os.path.join(BASE, "train", "ingest.py")
    cmd = [sys.executable, script, "--agents", agents, "--rows", str(rows)]
    print(f"running: {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, cwd=BASE)
    sys.exit(r.returncode)


def cmd_submit(kind, payload):
    if kind not in ("shell", "fetch", "python"):
        print(f"unknown kind: {kind} (shell|fetch|python)", file=sys.stderr)
        sys.exit(2)
    c = db()
    cur = c.execute("INSERT INTO tasks (kind, payload, created_at) VALUES (?,?,?)",
                    (kind, payload, time.time()))
    c.commit()
    print(cur.lastrowid)


def cmd_status():
    c = db()
    live = live_workers(c)
    counts = dict(c.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status").fetchall())
    agents = dict(c.execute("SELECT id, agent_id FROM workers").fetchall())
    print(f"workers alive: {len(live)}")
    for wid in sorted(live):
        print(f"  {wid:28} agent={agents.get(wid, '-')}")
    print("queue: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) or "empty")
    for tid, kind, status, worker, att in c.execute(
            "SELECT id, kind, status, worker, attempts FROM tasks ORDER BY id DESC LIMIT 8"):
        print(f"  #{tid} {kind:7} {status:8} {worker or '-':24} attempts={att}")


def cmd_result(tid):
    c = db()
    row = c.execute("SELECT kind, status, worker, attempts, result, payload FROM tasks WHERE id=?",
                    (tid,)).fetchone()
    if not row:
        print("no such task")
        return
    kind, status, worker, att, result, payload = row
    print(f"task #{tid} [{kind}] status={status} worker={worker} attempts={att}")
    print(f"payload: {payload}")
    if result:
        r = json.loads(result)
        print(f"ok: {r.get('ok')}  agent: {r.get('agent')}")
        ctx = r.get("skill_context") or []
        if ctx:
            print("--- skill context (FTS top hits) ---")
            for h in ctx:
                print(f"  [{h['agent_id']}/{h['dataset']}] {h['snippet'][:160]}")
        if r.get("output"):
            print("--- output ---")
            print(r["output"][-4000:])
        if r.get("error"):
            print("--- error ---")
            print(r["error"][-2000:])


def cmd_results(n):
    c = db()
    for tid, kind, status, finished in c.execute(
            "SELECT id, kind, status, finished_at FROM tasks WHERE status IN ('done','failed')"
            " ORDER BY id DESC LIMIT ?", (n,)):
        when = time.strftime("%H:%M:%S", time.localtime(finished)) if finished else "-"
        print(f"#{tid} {kind:7} {status:6} finished={when}")


def cmd_wait(tid, timeout):
    c = db()
    end = time.time() + timeout
    while time.time() < end:
        row = c.execute("SELECT status FROM tasks WHERE id=?", (tid,)).fetchone()
        if row and row[0] in ("done", "failed"):
            cmd_result(tid)
            return
        time.sleep(1)
    print(f"timeout waiting for task #{tid}")


# ---------------- skill lookup (lightweight FTS) ----------------

def skill_lookup(payload_text, limit=3):
    """Query knowledge/index.db with keywords from the task payload.
    Returns top hits as [{agent_id, dataset, snippet}]. Silent [] if no index."""
    if not os.path.exists(INDEXDB):
        return []
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_\-]{3,}", payload_text.lower())
    terms = [w for w in dict.fromkeys(words) if w not in STOPWORDS][:10]
    if not terms:
        return []
    q = " OR ".join(f'"{t}"' for t in terms)
    try:
        c = sqlite3.connect(INDEXDB, timeout=10)
        rows = c.execute(
            """SELECT agent_id, dataset,
                      snippet(docs, 2, '', '', ' … ', 24)
               FROM docs WHERE docs MATCH ? ORDER BY bm25(docs) LIMIT ?""",
            (q, limit)).fetchall()
        c.close()
        return [{"agent_id": a, "dataset": d, "snippet": s} for a, d, s in rows]
    except Exception:
        return []


# ---------------- worker ----------------

def worker_main(wid, aid):
    prof = {}
    pp = os.path.join(AGENTSDIR, f"{aid}.json")
    if os.path.exists(pp):
        prof = json.load(open(pp))
    c = db()
    c.execute("UPDATE workers SET pid=?, agent_id=?, last_heartbeat=? WHERE id=?",
              (os.getpid(), aid, time.time(), wid))
    c.commit()
    print(f"[{wid}] started pid={os.getpid()} agent={aid} "
          f"({prof.get('name', '?')} / {prof.get('specialty', '?')})", flush=True)
    while True:
        try:
            c.execute("UPDATE workers SET last_heartbeat=? WHERE id=?", (time.time(), wid))
            c.execute("""UPDATE tasks SET status='pending', worker=NULL
                         WHERE status='running' AND claimed_at < ?""",
                      (time.time() - STALE_AFTER,))
            now = time.time()
            cur = c.execute("""UPDATE tasks SET status='running', worker=?,
                               attempts=attempts+1, started_at=?, claimed_at=?
                               WHERE id = (SELECT id FROM tasks WHERE status='pending'
                                           ORDER BY id LIMIT 1)""",
                            (wid, now, now))
            c.commit()
            if cur.rowcount == 0:
                time.sleep(2)
                continue
            tid, kind, payload = c.execute(
                "SELECT id, kind, payload FROM tasks WHERE worker=? AND status='running'"
                " ORDER BY claimed_at DESC LIMIT 1", (wid,)).fetchone()
            print(f"[{wid}] task #{tid} ({kind}) agent={aid}", flush=True)
            ctx = skill_lookup(payload)
            for h in ctx:
                print(f"[{wid}] skill ctx [{h['agent_id']}/{h['dataset']}] "
                      f"{h['snippet'][:120]}", flush=True)
            res = execute(kind, json.loads(payload))
            res["agent"] = aid
            res["skill_context"] = ctx
            c.execute("UPDATE tasks SET status=?, result=?, finished_at=? WHERE id=?",
                      ("done" if res["ok"] else "failed", json.dumps(res), time.time(), tid))
            c.commit()
            print(f"[{wid}] task #{tid} -> {'done' if res['ok'] else 'failed'}", flush=True)
        except Exception as e:  # never let the worker die on a bad task
            try:
                c.rollback()
            except Exception:
                pass
            print(f"[{wid}] worker error: {e}", flush=True)
            time.sleep(2)


def execute(kind, p):
    try:
        if kind == "shell":
            r = subprocess.run(p["cmd"], shell=True, capture_output=True, text=True,
                               timeout=p.get("timeout", 120))
            return {"ok": r.returncode == 0,
                    "output": (r.stdout + r.stderr)[-8000:],
                    "error": "" if r.returncode == 0 else f"exit={r.returncode}"}
        if kind == "fetch":
            out = p.get("out") or os.path.join(LOGDIR, f"fetch-{uuid.uuid4().hex[:8]}")
            r = subprocess.run(["curl", "-sS", "-L", "--max-time", str(p.get("timeout", 60)),
                                "-o", out, "-w", "%{http_code} %{size_download}", p["url"]],
                               capture_output=True, text=True, timeout=p.get("timeout", 60) + 10)
            return {"ok": r.returncode == 0,
                    "output": f"saved to {out} | {r.stdout.strip()}",
                    "error": r.stderr.strip()[-500:]}
        if kind == "python":
            r = subprocess.run([sys.executable, "-c", p["code"]], capture_output=True,
                               text=True, timeout=p.get("timeout", 120))
            return {"ok": r.returncode == 0,
                    "output": (r.stdout + r.stderr)[-8000:],
                    "error": "" if r.returncode == 0 else f"exit={r.returncode}"}
        return {"ok": False, "output": "", "error": f"unknown kind {kind}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "", "error": "timeout"}
    except Exception as e:
        return {"ok": False, "output": "", "error": str(e)[:500]}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("up"); u.add_argument("-n", type=int, default=4)
    sub.add_parser("down")
    t = sub.add_parser("train")
    t.add_argument("--agents", default="all")
    t.add_argument("--rows", type=int, default=200)
    s = sub.add_parser("submit"); s.add_argument("kind"); s.add_argument("payload")
    sub.add_parser("status")
    r = sub.add_parser("result"); r.add_argument("id", type=int)
    rs = sub.add_parser("results"); rs.add_argument("-n", type=int, default=10)
    w = sub.add_parser("wait"); w.add_argument("id", type=int)
    w.add_argument("--timeout", type=int, default=120)
    wr = sub.add_parser("worker"); wr.add_argument("--id", required=True)
    wr.add_argument("--agent", default="devops-01")
    a = ap.parse_args()
    if a.cmd == "up": cmd_up(a.n)
    elif a.cmd == "down": cmd_down()
    elif a.cmd == "train": cmd_train(a.agents, a.rows)
    elif a.cmd == "submit": cmd_submit(a.kind, a.payload)
    elif a.cmd == "status": cmd_status()
    elif a.cmd == "result": cmd_result(a.id)
    elif a.cmd == "results": cmd_results(a.n)
    elif a.cmd == "wait": cmd_wait(a.id, a.timeout)
    elif a.cmd == "worker": worker_main(a.id, a.agent)


if __name__ == "__main__":
    main()
