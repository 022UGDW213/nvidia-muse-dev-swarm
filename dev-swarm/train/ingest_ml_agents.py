#!/usr/bin/env python3
"""Ingest ML / LLM / swarm / MCP training data from Hugging Face.

Follows train/ingest_design.py's proven transport: curl through the egress
proxy to datasets-server /parquet (verify) and /rows (fetch). huggingface_hub
is broken here (urllib can't parse the proxy URL), so everything goes via curl.

Four lanes, one jsonl each (agent_id = lane id), additive to the shared FTS5
index built by build_index() from ALL knowledge/*.jsonl.

Usage: python3 train/ingest_ml_agents.py
"""
import json, os, re, sys
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "train"))
from ingest import dataset_exists, fetch_rows, build_index  # noqa: E402

KNOW = os.path.join(BASE, "knowledge")

SKIPPED = {
    # ML lane
    "dakwi/hyperparameter-optimization-dataset":
        "text field holds chess move sequences, not ML hyperparameter knowledge",
    "cShahar/nas-benchmarks": "not served by datasets-server (/parquet empty)",
    # LLM lane
    "Salesforce/xlam-function-calling-60k": "gated repo (auto), requires click-through",
    "Trelis/function_calling_extended": "gated repo (manual), requires click-through",
    # swarm lane
    "DeepNLP/Multi-Agents-Parallel-Orchestration-Dataset":
        "not served by datasets-server (/parquet empty)",
    # MCP lane
    "PolicyLayer/mcp-server-catalogue": "not served by datasets-server (/parquet empty)",
    "automatelab/mcp-servers-tool-catalog": "not served by datasets-server (/parquet empty)",
}

MAX_DOC = 3000
MIN_DOC = 100


def clip(v, n):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]


def msg_role(m):
    if not isinstance(m, dict):
        return "?"
    return str(m.get("role") or m.get("from") or m.get("type") or "?").lower()


def msg_text(m, n=700):
    if not isinstance(m, dict):
        return clip(m, n)
    c = m.get("content")
    if c is None:
        c = m.get("text") or m.get("value") or m.get("output") or ""
    if isinstance(c, list):
        parts = []
        for p in c:
            if isinstance(p, dict):
                parts.append(p.get("text") or p.get("content") or "")
            else:
                parts.append(str(p))
        c = " ".join(parts)
    return clip(c, n)


def convo_digest(msgs, max_msgs=6):
    """ROLE: text lines for the first N messages."""
    out = []
    if isinstance(msgs, list):
        for m in msgs[:max_msgs]:
            t = msg_text(m)
            if t:
                out.append(f"{msg_role(m).upper()}: {t}")
    return "\n".join(out)


def tool_names(tools):
    """Extract tool names from the many shapes tools take."""
    names = []
    if isinstance(tools, str):
        try:
            tools = json.loads(tools)
        except Exception:
            # raw schema text: pull "name" fields
            return re.findall(r'"name"\s*:\s*"([^"]+)"', tools)[:8]
    items = tools if isinstance(tools, list) else [tools]
    for t in items:
        if not isinstance(t, dict):
            continue
        fn = t.get("function", t)
        n = fn.get("name") if isinstance(fn, dict) else None
        if n:
            names.append(str(n))
    return names[:8]


# ---------------------------------------------------------------- ML lane

def doc_odyn(row):
    keys = ["id", "model", "model_size_b", "base_precision", "lora_rank",
            "lora_alpha_effective", "lora_dropout", "learning_rate",
            "num_epochs", "batch_size", "grad_accum", "seq_len",
            "gradient_checkpointing", "dataset_samples", "dataset"]
    parts = [f"{k}={clip(row.get(k, '?'), 40)}" for k in keys if row.get(k) not in (None, "")]
    if len(parts) < 5:
        return None
    return ("LORA FINE-TUNE CONFIG:\n" + ", ".join(parts) +
            "\nVerified hyperparameter set from the LoRA benchmark corpus.")


def doc_mlops(row):
    feats = ["Air temperature [K]", "Process temperature [K]",
             "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]", "Type"]
    have = [f"{f}={row.get(f)}" for f in feats if row.get(f) is not None]
    if len(have) < 4:
        return None
    verdict = "FAILURE" if row.get("prediction") == 1 else "no failure"
    return ("MLOPS MONITORING RECORD (predictive maintenance):\n" +
            ", ".join(have) + f" -> model prediction: {verdict} ({row.get('prediction')}).\n"
            "Telemetry features feeding a production failure-classification model.")


# ---------------------------------------------------------------- LLM lane

def doc_hermes(row):
    names = tool_names(row.get("tools"))
    body = convo_digest(row.get("conversations"))
    t = (f"TOOL-USE EXAMPLE [{clip(row.get('category'),60)} / "
         f"{clip(row.get('subcategory'),60)}]\n"
         f"Task: {clip(row.get('task'),120)}\n"
         f"TOOLS: {', '.join(names) or '(unparsed)'}\n"
         f"DIALOGUE:\n{body}")
    return t if len(t) >= MIN_DOC else None


def doc_glaive(row):
    sys_txt = clip(row.get("system"), 1200)
    names = tool_names(sys_txt)
    chat = clip(row.get("chat"), 1200)
    t = (f"FUNCTION-CALLING EXAMPLE\nTOOLS: {', '.join(names) or '(see schema)'}\n"
         f"SCHEMA+INSTRUCTIONS:\n{sys_txt}\n\nDIALOGUE:\n{chat}")
    return t if len(t) >= MIN_DOC else None


def doc_nemotron(row):
    ea = row.get("expected_action") or {}
    ar = row.get("agent_ref") or {}
    info = row.get("info") or {}
    t = (f"AGENTIC TOOL-USE TRAJECTORY #{row.get('trajectory_id')} "
         f"(turn {info.get('turn')}, step {info.get('step')})\n"
         f"Agent: {clip(ar.get('name') or ar, 80)}\n"
         f"EXPECTED ACTION [{ea.get('type')}]: {clip(ea.get('content'), 1100)}\n"
         "LESSON: when available tools cannot do the job, the agent must say "
         "so explicitly instead of hallucinating a result.")
    return t if len(t) >= MIN_DOC else None


def doc_stindard(row):
    meta = row.get("metadata") or {}
    names = tool_names(row.get("tools"))
    body = convo_digest(row.get("messages"))
    t = (f"TOOL-CALL RECORD [{clip(meta.get('category'),40)}]\n"
         f"tool_calls={meta.get('num_tool_calls')} parallel={meta.get('parallel_calls')} "
         f"multiturn={meta.get('multiturn')} no_tool_needed={meta.get('no_tool_needed')}\n"
         f"TOOLS: {', '.join(names)}\nDIALOGUE:\n{body}")
    return t if len(t) >= MIN_DOC else None


# ---------------------------------------------------------------- swarm lane

def doc_fable5(row):
    msgs = row.get("messages") or []
    roles = [msg_role(m) for m in msgs]
    flow = " -> ".join(roles[:10]) + (" ..." if len(roles) > 10 else "")
    tool_calls = [m for m in msgs if msg_role(m) == "tool"]
    tool_names_seen = []
    for m in tool_calls[:6]:
        t = msg_text(m, 120)
        tool_names_seen.append(t.split(":")[0][:40] if ":" in t else t[:40])
    first_asst = next((msg_text(m) for m in msgs if msg_role(m) == "assistant" and msg_text(m)), "")
    meta = row.get("meta") or {}
    t = (f"SWARM AGENT TRACE (source={meta.get('source')}, {len(msgs)} messages)\n"
         f"ROLE FLOW: {flow}\n"
         f"TOOL CALLS: {len(tool_calls)}"
         f" ({', '.join(tool_names_seen) or 'n/a'})\n"
         f"FIRST ASSISTANT ACTION: {clip(first_asst, 900)}\n"
         "Pattern: long multi-turn coding-agent session with interleaved tool results.")
    return t if len(t) >= MIN_DOC else None


def doc_agwf(row):
    meta = row.get("metadata") or {}
    body = convo_digest(row.get("conversations"))
    t = (f"AGENTIC WORKFLOW EXAMPLE [{clip(meta.get('category'),60)}]\n"
         f"Context: {clip(meta.get('context'),120)}\nDIALOGUE:\n{body}")
    return t if len(t) >= MIN_DOC else None


def doc_bidding(row):
    p = clip((row.get("prompts") or [""])[0], 900)
    g = clip((row.get("generations") or [""])[0], 1400)
    t = (f"MULTI-AGENT DIALOGUE (bidding/debate format)\nSETUP:\n{p}\n\n"
         f"AGENT TURNS:\n{g}")
    return t if len(t) >= MIN_DOC else None


def doc_crewai(row):
    t = clip(row.get("text"), 1200)
    if len(t) < 60:
        return None
    return "AGENT ROLE PROFILE (CrewAI):\n" + t


# ---------------------------------------------------------------- MCP lane

def doc_mcplogs(row):
    t = (f"MCP SESSION LOG\nclient={clip(row.get('name'),40)} v{clip(row.get('version'),20)} "
         f"ip={clip(row.get('ipAddress'),20)} authorized={row.get('authorized')}\n"
         f"method={clip(row.get('methodName'),40)} session={clip(row.get('sessionId'),12)}...\n"
         f"REQUEST: {clip(row.get('requestJson'), 700)}\n"
         f"RESPONSE: {clip(row.get('responseJson'), 700)}")
    return t if len(t) >= MIN_DOC else None


def doc_bench(row):
    keys = ["scenario_id", "server", "protocol", "tool", "virtual_users",
            "concurrency_limit", "duration_s", "total_requests",
            "successful_requests", "failed_requests", "requests_per_second",
            "avg_latency_ms", "p95_latency_ms", "p99_latency_ms"]
    parts = [f"{k}={clip(row.get(k), 40)}" for k in keys
             if row.get(k) not in (None, "", "None")]
    t = "MCP SERVER LOAD TEST:\n" + ", ".join(parts)
    return t if len(t) >= MIN_DOC else None


def doc_catalog(row):
    desc = clip(row.get("description"), 1100)
    t = (f"MCP SERVER CATALOG: {clip(row.get('content_name'),60)} "
         f"[{clip(row.get('subfield'),40)}]\n{desc}")
    return t if len(t) >= MIN_DOC else None


LANES = [
    ("ml-training", [
        {"id": "odyn-network/lora-hyperparameter-benchmark-v1", "rows": 200, "fn": doc_odyn},
        {"id": "pgurazada1/machine-failure-mlops-demo-logs", "rows": 100, "fn": doc_mlops},
    ]),
    ("llm-ops", [
        {"id": "NousResearch/hermes-function-calling-v1", "rows": 200,
         "cfg": "func_calling_singleturn", "fn": doc_hermes},
        {"id": "glaiveai/glaive-function-calling-v2", "rows": 150, "fn": doc_glaive},
        {"id": "nvidia/Nemotron-RL-Agentic-Function-Calling-Pivot-v1", "rows": 150,
         "fn": doc_nemotron},
        {"id": "stindardlogic/tool-calling-english-100k", "rows": 150, "fn": doc_stindard},
    ]),
    ("swarm-multiagent", [
        {"id": "Swarm-AI-Research/fable5-traces-sft", "rows": 120, "fn": doc_fable5},
        {"id": "stindardlogic/agentic-workflows-sft-100k", "rows": 150, "fn": doc_agwf},
        {"id": "LangChainDatasets/multiagent-bidding-dialogue", "rows": 100, "fn": doc_bidding},
        {"id": "DrDrek/crewai_finetuning_dataset", "rows": 100, "fn": doc_crewai},
    ]),
    ("mcp-protocol", [
        {"id": "hf-mcp-server/test-mcp-logs", "rows": 200,
         "cfg": "sessions", "split": "sessions", "fn": doc_mcplogs},
        {"id": "kshitijthakkar/mcp-server-bench", "rows": 150, "fn": doc_bench},
        {"id": "DeepNLP/mcp-servers", "rows": 150, "fn": doc_catalog},
    ]),
]


def main():
    os.makedirs(KNOW, exist_ok=True)
    stats = Counter()
    all_notes = {}
    for lane, dss in LANES:
        docs, notes = [], {}
        for cfg in dss:
            ds_id = cfg["id"]
            avail = dataset_exists(ds_id)
            if not avail:
                notes[ds_id] = {"status": "skipped", "rows": 0,
                                "note": "not served by datasets-server"}
                print(f"[{ds_id}] skipped: not served", flush=True)
                continue
            cfg_name = cfg.get("cfg") or avail[0][0]
            split = cfg.get("split") or avail[0][1]
            try:
                rows = fetch_rows(ds_id, cfg_name, split, cfg["rows"])
            except Exception as e:
                notes[ds_id] = {"status": "skipped", "rows": 0,
                                "note": f"/rows failed: {str(e)[:80]}"}
                print(f"[{ds_id}] skipped: {e}", flush=True)
                continue
            n = 0
            for row in rows:
                try:
                    t = cfg["fn"](row)
                except Exception:
                    continue
                if not t or len(t) < MIN_DOC:
                    continue
                if len(t) > MAX_DOC:
                    t = t[:MAX_DOC] + "…"
                docs.append({"agent_id": lane, "dataset": ds_id, "text": t})
                n += 1
            notes[ds_id] = {"status": "ok", "rows": n,
                            "note": f"{cfg_name}/{split}"}
            print(f"[{ds_id}] {n} docs", flush=True)
        out = os.path.join(KNOW, f"{lane}.jsonl")
        with open(out, "w") as f:
            for d in docs:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        all_notes[lane] = notes
        stats[lane] = len(docs)

    manifest_path = os.path.join(KNOW, "manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    manifest["ml-llm-swarm-mcp"] = {
        "docs": dict(stats),
        "datasets": all_notes,
        "skipped": SKIPPED,
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    n = build_index()
    print(f"lanes: {dict(stats)}; index now holds {n} docs total", flush=True)


if __name__ == "__main__":
    main()
