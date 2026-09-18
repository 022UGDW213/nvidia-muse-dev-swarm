#!/usr/bin/env python3
"""Ingest web-designer training data from Hugging Face into the dev-swarm FTS5 index.

Follows the same transport as train/ingest.py: curl through the egress proxy to
datasets-server /parquet (verify) and /rows (fetch). huggingface_hub is broken
here (urllib can't parse the proxy URL), so everything goes through curl.

Design rows carry huge code blobs (18-89KB of HTML/CSS). Instead of the generic
flatten-and-truncate, this script builds a "design digest" per row:
  - DESIGN INTENT: the full instruction/prompt/user brief (the design thinking)
  - DESIGN PATTERNS: code lines containing design-relevant CSS tokens
    (backdrop-filter, glass, gradients, shadows, radii, transitions, layout,
     typography, color) — capped so each doc stays retrievable and on-topic.

Output: knowledge/design-web.jsonl (agent_id="design-web"), then the shared
FTS5 index is rebuilt from ALL knowledge/*.jsonl (additive to the DevOps docs).

Usage: python3 train/ingest_design.py
"""
import json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "train"))
from ingest import (  # noqa: E402  (reuse: curl transport, fetch, index build)
    curl_json, dataset_exists, fetch_rows, build_index)

KNOW = os.path.join(BASE, "knowledge")

DESIGN_DATASETS = [
    # instruction -> real-website section code (hero, navbar, cards...)
    {"id": "InstateLabs/website-code-dataset", "rows": 200,
     "intent_keys": ("instruction",), "code_keys": ("output",)},
    # prompt -> full generated landing pages (Tailwind, modern styles)
    {"id": "VortexHunter23/Modern_Website_Code_Generator", "rows": 150,
     "intent_keys": ("prompt",), "code_keys": ("response",)},
    # expert web-designer briefs -> polished self-contained HTML sites
    {"id": "r333ddd/mad-web-design-selected-samples", "rows": 100,
     "intent_keys": ("messages",), "code_keys": ("messages",)},
    # design brief -> one-file pages (incl. developer portfolios)
    {"id": "finnianx/webdesign", "rows": 100,
     "intent_keys": ("prompt",), "code_keys": ("completion",)},
]

SKIPPED = {
    "web-genie-ai/Design2Code-hf": "not served by datasets-server (/parquet empty)",
    "obaydata/design-repo-web-design-benchmark": "not served by datasets-server (/parquet empty)",
    "dhanushkaha/web_designs": "image-only rows, no textual design knowledge",
    "JoshPurtell/web-design-screenshots": "image-only rows, no textual design knowledge",
    "shellcoochi/webDesigner": "Chinese low-code naiveUI schema; niche, not general web design",
    "Kukedlc/web-design-diamond": "Spanish-dominant; low value for English FTS retrieval",
}

# CSS tokens that carry actual design decisions (not resets/boilerplate)
DESIGN_TOKENS = re.compile(
    r"backdrop-filter|glass|frosted|blur\(|saturat|gradient|box-shadow|"
    r"text-shadow|border-radius|border:|transition|animation|@keyframes|"
    r"transform|hover|opacity|rgba\(|hsla\(|font-family|font-size|"
    r"font-weight|letter-spacing|line-height|clamp\(|var\(--|grid|flex|"
    r"gap:|padding|backdrop|inset|z-index|overflow|::before|::after|"
    r"mask|mix-blend|filter:", re.I)

BOILERPLATE = re.compile(
    r"<!doctype|<html|<head|<meta|</head>|<body|</body>|</html>|"
    r"-webkit-text-size-adjust|-ms-text-size-adjust|article,aside|"
    r"audio,|video,|canvas|svg|@charset|@import url\(https?://fonts",
    re.I)

MAX_LINES = 60
MAX_DOC = 4000


def chat_flatten(v):
    """Pull user/assistant text out of chat-style message lists."""
    out = []
    if isinstance(v, list):
        for m in v:
            if isinstance(m, dict):
                role = str(m.get("role", "")).lower()
                c = m.get("content")
                if isinstance(c, str) and c.strip():
                    tag = "BRIEF" if role == "user" else "RESPONSE"
                    out.append(f"[{tag}] {c.strip()[:1200]}")
    return "\n".join(out)


def intent_text(row, keys):
    parts = []
    for k in keys:
        v = row.get(k)
        if isinstance(v, str) and len(v.strip()) > 10:
            parts.append(v.strip()[:1200])
        elif isinstance(v, list):
            parts.append(chat_flatten(v))
    return "\n".join(p for p in parts if p).strip()


def pattern_lines(code):
    """Keep only lines that contain design decisions."""
    lines, seen = [], set()
    for raw in str(code).splitlines():
        line = raw.strip()
        if len(line) < 8 or len(line) > 400:
            continue
        if BOILERPLATE.search(line):
            continue
        if not DESIGN_TOKENS.search(line):
            continue
        key = line[:80]
        if key in seen:
            continue
        seen.add(key)
        lines.append(line)
        if len(lines) >= MAX_LINES:
            break
    return lines


def row_to_design_doc(row, cfg):
    intent = intent_text(row, cfg["intent_keys"])
    code_parts = []
    for k in cfg["code_keys"]:
        v = row.get(k)
        if isinstance(v, str):
            code_parts.append(v)
        elif isinstance(v, list):
            # chat style: keep assistant's code-bearing content
            for m in v:
                if isinstance(m, dict) and str(m.get("role", "")).lower() in (
                        "assistant", "response"):
                    c = m.get("content")
                    if isinstance(c, str):
                        code_parts.append(c)
    patterns = pattern_lines("\n".join(code_parts))
    if len(intent) < 20 and not patterns:
        return None
    doc = "DESIGN INTENT:\n" + (intent or "(none)") + \
        "\n\nDESIGN PATTERNS:\n" + ("\n".join(patterns) if patterns else "(none)")
    if len(doc) > MAX_DOC:
        doc = doc[:MAX_DOC] + "…"
    return doc


def main():
    os.makedirs(KNOW, exist_ok=True)
    docs, notes = [], {}
    for cfg in DESIGN_DATASETS:
        ds_id = cfg["id"]
        avail = dataset_exists(ds_id)
        if not avail:
            notes[ds_id] = {"status": "skipped", "rows": 0,
                            "note": "not served by datasets-server"}
            print(f"[{ds_id}] skipped: not served", flush=True)
            continue
        cfg_name, split = avail[0][0], avail[0][1]
        try:
            rows = fetch_rows(ds_id, cfg_name, split, cfg["rows"])
        except Exception as e:
            notes[ds_id] = {"status": "skipped", "rows": 0,
                            "note": f"/rows failed: {str(e)[:80]}"}
            print(f"[{ds_id}] skipped: {e}", flush=True)
            continue
        n = 0
        for row in rows:
            t = row_to_design_doc(row, cfg)
            if not t or len(t) < 120:
                continue
            docs.append({"agent_id": "design-web", "dataset": ds_id, "text": t})
            n += 1
        notes[ds_id] = {"status": "ok", "rows": n, "note": f"{cfg_name}/{split}"}
        print(f"[{ds_id}] {n} design docs", flush=True)

    out = os.path.join(KNOW, "design-web.jsonl")
    with open(out, "w") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    manifest_path = os.path.join(KNOW, "manifest.json")
    manifest = {}
    if os.path.exists(manifest_path):
        manifest = json.load(open(manifest_path))
    manifest["design-web"] = {
        "docs": len(docs),
        "datasets": {**notes,
                      **{k: {"status": "skipped", "rows": 0, "note": v}
                         for k, v in SKIPPED.items()}},
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    n = build_index()
    print(f"design-web: {len(docs)} docs written; index now holds {n} docs total",
          flush=True)


if __name__ == "__main__":
    main()
