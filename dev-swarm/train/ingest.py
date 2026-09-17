#!/usr/bin/env python3
"""Ingest small training samples from Hugging Face datasets for dev-swarm agents.

For each agent profile in agents/<id>.json:
  1. Verify each mapped dataset exists via datasets-server /parquet endpoint.
  2. Pull a small sample of rows via datasets-server /rows (paged, ~200 rows/dataset).
  3. Convert rows to JSONL at knowledge/<agent-id>.jsonl  (agent_id, dataset, text).
  4. Rebuild the shared FTS5 index at knowledge/index.db from all JSONL files.

All HTTP goes through curl (the VM's egress proxy breaks python urllib).
No API keys. Total download is a few MB.

Usage:
  ingest.py --agents all            # all 30 agents
  ingest.py --agents devops-01,devops-02
  ingest.py --agents devops-01 --rows 100
"""
import argparse, json, os, sqlite3, subprocess, sys, tempfile

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS_DIR = os.path.join(BASE, "agents")
KNOW = os.path.join(BASE, "knowledge")
PARQUET_API = "https://datasets-server.huggingface.co/parquet"
ROWS_API = "https://datasets-server.huggingface.co/rows"
FALLBACK = {"id": "tatsu-lab/alpaca", "config": "default", "split": "train"}
STOPWORDS = set("""a an the and or of to in on for with is are was were be been
being it its this that these those as at by from into over after before between
you your we they them he she his her our their not no do does did will would
can could should have has had how what when where which who whom whose why if
then than so such only also just more most other some any all each every per
via using use used make made into out up down about into""".split())

MAX_TEXT = 1500  # chars per doc


def curl_json(url, params):
    cmd = ["curl", "-s", "--max-time", "40", "-G", url]
    for k, v in params.items():
        cmd += ["--data-urlencode", f"{k}={v}"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError(f"curl failed: {r.stderr[:200]}")
    return json.loads(r.stdout or "{}")


def dataset_exists(ds_id):
    """Verify via /parquet; returns list of (config, split) or None."""
    try:
        p = curl_json(PARQUET_API, {"dataset": ds_id})
    except Exception:
        return None
    files = p.get("parquet_files") or []
    if not files:
        return None
    seen = []
    for f in files:
        k = (f.get("config"), f.get("split"))
        if k not in seen:
            seen.append(k)
    return seen


def fetch_rows(ds_id, config, split, want):
    """Page /rows; returns list of row dicts."""
    rows, offset, page = [], 0, 100
    while len(rows) < want:
        r = curl_json(ROWS_API, {"dataset": ds_id, "config": config,
                                "split": split, "offset": offset,
                                "length": min(page, want - len(rows))})
        batch = r.get("rows") or []
        if not batch:
            break
        rows += [b.get("row", {}) for b in batch]
        if len(batch) < page:
            break
        offset += page
    return rows


def row_to_text(row):
    """Flatten a dataset row into a short text doc."""
    parts = []

    def add(v):
        if isinstance(v, str) and len(v.strip()) > 15:
            parts.append(v.strip())
        elif isinstance(v, list):
            for x in v:
                add(x)
        elif isinstance(v, dict):
            # chat-style: {"role":..,"content":..} or {"from":..,"value":..}
            for k in ("content", "value", "text"):
                if isinstance(v.get(k), str):
                    add(v[k])

    for v in row.values():
        add(v)
    text = "\n".join(parts)
    # drop boilerplate-ish super long single fields
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT] + "…"
    return text


def ingest_agent(aid, rows_per_ds, manifest):
    prof = json.load(open(os.path.join(AGENTS_DIR, f"{aid}.json")))
    out_path = os.path.join(KNOW, f"{aid}.jsonl")
    docs, notes = [], {}
    tried = list(prof["hf_datasets"])
    for entry in tried:
        ds_id = entry["id"]
        avail = dataset_exists(ds_id)
        if not avail:
            notes[ds_id] = {"status": "skipped", "rows": 0,
                            "note": "not served by datasets-server"}
            continue
        cfg = entry.get("config") or avail[0][0]
        split = entry.get("split") or "train"
        if not any(c == cfg and s == split for c, s in avail):
            cfg, split = avail[0]  # mapped config missing -> first available
            notes[ds_id] = {"status": "config-substituted", "rows": 0,
                            "note": f"using {cfg}/{split}"}
        try:
            rows = fetch_rows(ds_id, cfg, split, rows_per_ds)
        except Exception as e:
            notes.setdefault(ds_id, {})["status"] = "skipped"
            notes[ds_id]["note"] = f"/rows failed: {str(e)[:80]}"
            notes[ds_id]["rows"] = 0
            continue
        n = 0
        for row in rows:
            t = row_to_text(row)
            if len(t) < 40:
                continue
            docs.append({"agent_id": aid, "dataset": ds_id, "text": t})
            n += 1
        st = notes.get(ds_id, {})
        st.update({"status": "ok", "rows": n,
                   "note": st.get("note", f"{cfg}/{split}")})
        notes[ds_id] = st
    if not docs:
        # guaranteed fallback so no agent ends up empty
        try:
            rows = fetch_rows(FALLBACK["id"], FALLBACK["config"],
                              FALLBACK["split"], rows_per_ds)
            for row in rows:
                t = row_to_text(row)
                if len(t) >= 40:
                    docs.append({"agent_id": aid, "dataset": FALLBACK["id"],
                                 "text": t})
            notes[FALLBACK["id"]] = {"status": "fallback", "rows": len(docs),
                                     "note": "mapped datasets unavailable"}
        except Exception as e:
            notes[FALLBACK["id"]] = {"status": "failed", "rows": 0,
                                     "note": str(e)[:80]}
    with open(out_path, "w") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    manifest[aid] = {"docs": len(docs), "datasets": notes}
    print(f"[{aid}] {len(docs)} docs -> {os.path.basename(out_path)}", flush=True)
    return len(docs)


def build_index():
    db_path = os.path.join(KNOW, "index.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    c = sqlite3.connect(db_path)
    c.execute("CREATE VIRTUAL TABLE docs USING fts5(agent_id, dataset, text)")
    n = 0
    for fn in sorted(os.listdir(KNOW)):
        if not fn.endswith(".jsonl"):
            continue
        with open(os.path.join(KNOW, fn)) as f:
            batch = [(json.loads(l)["agent_id"], json.loads(l)["dataset"],
                      json.loads(l)["text"]) for l in f if l.strip()]
        c.executemany("INSERT INTO docs VALUES (?,?,?)", batch)
        n += len(batch)
    c.commit()
    c.execute("INSERT INTO docs(docs) VALUES('optimize')")
    c.commit()
    c.close()
    print(f"index rebuilt: {n} docs -> index.db", flush=True)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agents", default="all",
                    help="'all' or comma-separated ids like devops-01,devops-02")
    ap.add_argument("--rows", type=int, default=200,
                    help="rows per dataset (default 200)")
    a = ap.parse_args()
    os.makedirs(KNOW, exist_ok=True)
    if a.agents == "all":
        ids = [f"devops-{i:02d}" for i in range(1, 31)]
    else:
        ids = [x.strip() for x in a.agents.split(",") if x.strip()]
    manifest_path = os.path.join(KNOW, "manifest.json")
    manifest = {}
    if os.path.exists(manifest_path):
        manifest = json.load(open(manifest_path))
    total = 0
    for aid in ids:
        if not os.path.exists(os.path.join(AGENTS_DIR, f"{aid}.json")):
            print(f"[{aid}] no such agent profile, skipping", flush=True)
            continue
        total += ingest_agent(aid, a.rows, manifest)
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    n = build_index()
    # disk usage
    du = subprocess.run(["du", "-sh", KNOW], capture_output=True,
                        text=True).stdout.strip()
    print(f"done: {total} new docs, index holds {n} docs, knowledge base: {du}")


if __name__ == "__main__":
    main()
