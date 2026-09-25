#!/usr/bin/env python3
"""Ingest Muse Code SDK knowledge + agentic-coding datasets for dev-swarm.

Lane: muse-code-sdk. Additive to the shared FTS5 index.

Two halves:
  A) Repo-derived docs (~12 hand-written, from reading the cloned repo at
     ~/workspace/muse-code-sdk): what the SDK is, API surface (facade
     modules), MSP protocol concepts, session/turn lifecycle, approval and
     userInput dual-channel patterns, resume/retry/durability rules, and the
     conformance-fixture testing model.
  B) Hugging Face datasets (~160 rows each), verified served + ungated:

     glaiveai/glaive-function-calling-v2     tool-calling trajectories
     (system + chat) — function-call JSON patterns, the same shape the
     agent uses when the host routes tool calls through approvals.
     microsoft/orca-agentinstruct-1M-v1      agentic coding instructions
     (split code_) — instructions + agent-style answers for coding tasks.
     nvidia/OpenCodeReasoning                reasoning traces (input, output
     with chain-of-thought, solution, difficulty) — how agents work
     through a problem before emitting code.
     nvidia/OpenCodeInstruct                 instruction pairs + unit_tests
     (input, output, tests, score) — the verify-by-tests pattern that
     mirrors the SDK's own conformance testing.
     SWE-Gym/SWE-Gym                         real GitHub issue -> patch
     workflows (problem_statement, patch, FAIL_TO_PASS) — the
     reproduce-patch-verify loop every code agent runs.

Proven transport: curl through the egress proxy to datasets-server
/parquet (verify) and /rows (fetch). huggingface_hub is broken here
(urllib can't parse the proxy URL), so everything goes through curl.

Usage: python3 train/ingest_muse_sdk.py
"""
import json, os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "train"))
from ingest import dataset_exists, fetch_rows, build_index  # noqa: E402

KNOW = os.path.join(BASE, "knowledge")
LANE = "muse-code-sdk"
ROWS_PER_DS = 160
MIN_DOC = 100
MAX_DOC = 3000


def clip(v, n):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]


# ---------------------------------------------------------------- A) repo docs
REPO_DOCS = [
    ("sdk-identity",
     "MUSE CODE SDK — IDENTITY AND PURPOSE\n"
     "The Muse Code SDK (npm package @muse-code/sdk, MIT, Developer Preview, "
     "latest 1.3.0 published 2026-09-18) is Meta's TypeScript SDK for building clients that drive "
     "Muse Code agent sessions over the Muse Session Protocol (MSP). Repo: "
     "github.com/meta-models/muse-code-sdk. Docs: meta-models.github.io/muse-code-sdk.\n"
     "Install: npm install @muse-code/sdk (Node 20+, zero runtime deps).\n"
     "Pattern for a dev agent: never reinvent the agent — spawn a host process "
     "(`tbh serve` / `muse serve`), handshake, open sessions, stream turns, "
     "answer approval and userInput requests, survive host death, resume. "
     "The SDK is a facade over a JSON-RPC wire protocol; the repo's "
     "schema/msp/ directory holds the committed protocol declarations, a "
     "stable manifest, and recorded conformance transcripts the tests replay."),

    ("api-surface",
     "MUSE CODE SDK — API SURFACE (facade modules, from src/facade/ + src/index.ts)\n"
     "MuseClient (facade/client.js) — spawns and owns host connections; "
     "StartSessionOptions / ResumeSessionOptions.\n"
     "Session (facade/session.js) — session/new, session/list, session/resume, "
     "session/rename, session/setReasoningEffort.\n"
     "TurnSubmitter / turn-submit.js — send user turns; turn-handle.js gives "
     "Turn, TurnOutcome, isLaunchFailure.\n"
     "approval.js — the agent's permission-request flow.\n"
     "gap-fill.js — GapFillFailureHandler for sequence gaps.\n"
     "host-death.js — MuseHostDiedError, readSessionDurability.\n"
     "discarded.js — DiscardedSessions registry (cross-client sharing declined).\n"
     "fold/: ItemStore, SessionStateStore, SessionFold — client-side "
     "reconstruction of items and session state from the stream "
     "(DeltaApplyOutcome, StateApplyOutcome, PendingApproval).\n"
     "fingerprint.js — EXPECTED_SCHEMA_FINGERPRINT pinning and mismatch "
     "messages. connection/spawn.js — spawnMspConnection, ProcessExit, "
     "ExitClassification. Pattern: keep the SDK on the typed facade; reach "
     "for fold/* only when rebuilding UI state."),

    ("msp-protocol",
     "MUSE SESSION PROTOCOL (MSP) — WIRE CONCEPTS\n"
     "JSON-RPC over stdio to a child host process. Every client begins with "
     "a handshake it cannot skip: no traffic before the handshake completes "
     "(enforced by the type, not convention). The handshake describes the "
     "host and advertises its schema fingerprint; the SDK compares it with "
     "its pinned EXPECTED_SCHEMA_FINGERPRINT.\n"
     "Session lifecycle: session/new (with clientInfo {name, version} — name "
     "your client explicitly so recipes/journeys never inherit an identity "
     "by omission), session/list (display metadata: title, first user prompt, "
     "branch), session/rename, session/resume (runs the same startup "
     "reconciliation as a fresh launch so crash-orphaned work settles).\n"
     "Turns: submit a prompt, receive item/delta frames (live text keyed by "
     "itemId — append), item/completed (authoritative full text — replace "
     "your accumulation), turn/completed (terminal + usage). The turn is over "
     "on turn/completed, not on the last delta.\n"
     "Pattern: treat the protocol as the contract and the SDK as the typed "
     "enforcement of it — handshake first, stream deltas live, trust only "
     "completed frames."),

    ("approvals",
     "MUSE CODE SDK — APPROVAL FLOW (the dual-channel pattern integrators get wrong)\n"
     "When the agent needs permission (e.g. a tool call), the host asks "
     "TWICE for two audiences: approval/requested is a notification for your "
     "UI, approval/request is a JSON-RPC request your client MUST answer. "
     "If you never register a server-request handler, the SDK answers "
     "'method not found' on your behalf — so answer it.\n"
     "Answer with approval/decide, picking a choiceId the host OFFERED in "
     "availableChoices. Do not invent one; do not hardcode a choice the host "
     "may not offer for this subject.\n"
     "The ack is not the outcome: approval/resolved carries the decision, "
     "the policy result, and any session-scoped rule amendment.\n"
     "Denying is a normal answer, not an error — the turn keeps running and "
     "the agent tells the user what it did not do.\n"
     "Policy notes from the changelog: MCP tools a server declares read-only "
     "run without a prompt under on-request approvals; commands launched via "
     "wrappers (env, setsid) are reviewed as the command they actually "
     "launch; permission mode changes mid-session apply to already-running "
     "tools at their next action.\n"
     "Pattern for a dev agent: build your tool-gating UI exactly this way — "
     "view event for humans, protocol request for the agent, decision from "
     "the offered set, outcome read from the resolved frame."),

    ("userinput",
     "MUSE CODE SDK — AGENT ASKING THE USER (userInput flow)\n"
     "Mid-turn the agent can stop and ask the user a structured question via "
     "the request_user_input tool. Same dual-channel shape as approvals: "
     "userInput/requested is the view-stream event for your UI; "
     "userInput/request is the JSON-RPC request the SDK must answer (again, "
     "an unregistered handler means the SDK answers 'method not found').\n"
     "The reply means 'this client is showing the question', NOT 'here is "
     "the answer'. A pending question survives the client: a resumed session "
     "finds it in the resume result's pendingRequests, and the host re-issues "
     "userInput/request to the late joiner.\n"
     "Answer with userInput/answer, picking a selectedLabel the host offered "
     "in the question's options. The ack is not the outcome: userInput/settled "
     "is where the outcome, recorded answers, and deciding command land; "
     "then the tool call completes with the answer as visible output and the "
     "turn runs on.\n"
     "Pattern: pendingRequests on resume is your 'interrupted work inbox' — "
     "render it before streaming anything new."),

    ("resume-durability",
     "MUSE CODE SDK — RESUME, DURABILITY, HOST DEATH\n"
     "resume-and-verify recipe: a session is started by one host process, "
     "which is shut down cleanly; a SECOND host — a fresh process over the "
     "same state directory — resumes it. That is the real failure shape "
     "(your app restarted, or the host went away); canned transcripts cannot "
     "play it because only a real second host can.\n"
     "survive-the-host-dying recipe: hosts die (crash, OOM kill, stray "
     "signal) without asking your app first. Read sessionDurability off the "
     "handshake with readSessionDurability — it is the durability fork "
     "every embedder must get right. After a crash, a tool approval still "
     "waiting for an answer shows as UNRESOLVED on resume, never as already "
     "executed; pending approvals survive a headless restart instead of "
     "inheriting the predecessor's abort.\n"
     "classify-serve-exits recipe: every way `muse serve` can exit is "
     "classified — stderr is evidence a client captures and never parses, "
     "the exit code is the contract a client branches on when the process "
     "dies before or instead of answering (MuseServeChild.exit resolves to "
     "an ExitClassification).\n"
     "Pattern: durability is read at handshake, death is classified by exit "
     "code, and every pending human decision rehydrates as unresolved."),

    ("retry-idempotency",
     "MUSE CODE SDK — RETRY WITHOUT DOUBLE-SUBMITTING (idempotency)\n"
     "retry-without-double-submitting recipe (plays three golden transcripts; "
     "companion to the commands-and-idempotency guide): a failed command "
     "must be retryable without the host executing the user's turn twice.\n"
     "Connection.command verifies that acks echo the RECORDED commandId from "
     "the transcript; replies to one of your requests come back under the id "
     "YOU sent, so the SDK's request-id minting correlates replies exactly "
     "as against a real host.\n"
     "cancel-mid-turn recipe: cancel a running turn; the two writes around a "
     "server request are ordered and the fixture enforces it — a command that "
     "overtakes the reply is a frame divergence, not tolerated reordering.\n"
     "queue-steer-reclaim recipe: the multi-turn traffic rules every "
     "chat-style UI eventually hits (turn-unqueued-round-trip).\n"
     "Pattern: request ids correlate, commandIds verify against the record, "
     "writes around server requests stay ordered, and cancellation is a "
     "first-class command — wire these into any agent client you build."),

    ("conformance-testing",
     "MUSE CODE SDK — CONFORMANCE-FIXTURE TESTING MODEL (steal this)\n"
     "The repo's test strategy is the most transferable idea in it: "
     "`muse-conformance serve-fixture` is a canned stdio host that plays "
     "committed golden transcripts from schema/msp/transcripts/ "
     "(approval-round-trip, userinput-answer-round-trip, text-run-single-turn, "
     "turn-unqueued-round-trip, cancel-mid-turn, ...). Each cookbook recipe "
     "runs against a fixture, so every recipe is deterministic, needs no "
     "credentials and no model, and cannot go stale — the code you read in "
     "the docs IS the code that runs.\n"
     "The quickstart journey (sdk-quickstart/src/journey.ts) is the "
     "acceptance artifact: 12 segments (spawn, handshake, session-new, turn, "
     "approval, cancel, resume, ...), each asserting spec-correct behavior; "
     "where the host is wrong a segment carries an expectBlock naming the "
     "issue AND the failure signature, and a blocked segment that starts "
     "passing FAILS the journey so it gets promoted — expect-blocks cannot "
     "rot.\n"
     "A loopback fake first-party provider (provider.ts) lets acceptance run "
     "fully headless: real model turns against a fake endpoint, nothing "
     "leaves the machine.\n"
     "Pattern for a dev agent: golden transcripts + a fixture host + "
     "spec-pinned assertions is how you test agent-client code without "
     "flakes, keys, or models."),

    ("cookbook-map",
     "MUSE CODE SDK — COOKBOOK RECIPE MAP (clients/sdk-cookbook/src/recipes/)\n"
     "12 executable recipes, each self-documenting with a module header:\n"
     "stream-a-turn — append item/delta keyed by itemId; trust only "
     "item/completed and turn/completed.\n"
     "answer-user-input — the userInput dual-channel + pendingRequests.\n"
     "approve-or-deny — plays BOTH arms (deny is the one integrators get "
     "wrong); approval/requested vs approval/request.\n"
     "cancel-mid-turn — cancel a running turn.\n"
     "classify-serve-exits — stderr is evidence, exit code is contract.\n"
     "fingerprint-mismatch — mismatch is a WARNING, never an error "
     "(additive-optional schema evolution keeps an older SDK working).\n"
     "list-models-and-switch-mid-session — headless model catalog, no creds.\n"
     "queue-steer-reclaim — multi-turn traffic rules.\n"
     "resume-and-verify — two-host resume, the real failure shape.\n"
     "retry-without-double-submitting — idempotent command retry.\n"
     "survive-the-host-dying — readSessionDurability at handshake.\n"
     "Recipe kit (kit/host.ts, segments.ts, runner.ts): equality/object "
     "assertions over recorded frames — a mini golden-test harness.\n"
     "Pattern: when you need a behavior, copy the recipe's shape first, "
     "then adapt."),

    ("msp-ts-types",
     "MUSE CODE SDK — PROTOCOL TYPES (clients/msp-ts/)\n"
     "@muse-code/msp holds the generated MSP wire types; schema/msp/msp.d.ts "
     "is the committed declaration the SDK typechecks against "
     "(scripts/check-msp-ts-typecheck.sh). The docs reference pages are "
     "generated FROM this schema and the SDK's own type information, not "
     "hand-copied — so the reference cannot drift from the wire.\n"
     "EXPECTED_SCHEMA_FINGERPRINT pins the exact schema the SDK was written "
     "against; the handshake advertises the host's fingerprint. Mismatch "
     "posture: warn, keep working (additive-optional evolution), surface "
     "fingerprintMismatchMessage — never hard-fail.\n"
     "Pattern: generate reference docs and types from one schema source; pin "
     "the fingerprint at build; treat mismatch as advisory."),
]


def repo_docs():
    return [
        {"agent_id": LANE,
         "dataset": "meta-models/muse-code-sdk (repo)",
         "text": f"MUSE CODE SDK KNOWLEDGE — {name}\n{body}"}
        for name, body in REPO_DOCS
    ]


# ---------------------------------------------------------------- B) datasets

def doc_toolcall(row):
    """glaive function-calling: system + chat trajectory with tool calls."""
    chat = row.get("chat") or []
    turns = []
    for m in chat:
        if not isinstance(m, dict):
            continue
        role = m.get("role") or m.get("from") or "?"
        content = clip(m.get("content") or m.get("value"), 700)
        if content:
            turns.append(f"{role.upper()}: {content}")
    sys_txt = clip(row.get("system"), 300)
    body = "\n".join(turns)
    t = ("AGENTIC TOOL-CALLING TRAJECTORY (glaive-function-calling-v2):\n"
         f"SYSTEM: {sys_txt}\n{body}\n"
         "Pattern: a multi-turn tool-use conversation — system prompt sets "
         "the available functions, the assistant emits structured tool "
         "calls, results come back as tool messages. Same shape as a code "
         "agent driving tool calls through an approval flow: function "
         "schema first, structured call second, result third.")
    return t if len(t) >= MIN_DOC else None


def doc_orca(row):
    """orca-agentinstruct code split: messages with agentic coding answers."""
    msgs = row.get("messages") or []
    turns = []
    for m in msgs:
        if not isinstance(m, dict):
            continue
        role = m.get("role") or "?"
        content = clip(m.get("content"), 900)
        if content:
            turns.append(f"{role.upper()}: {content}")
    body = "\n".join(turns)
    t = ("AGENTIC CODING INSTRUCTION (microsoft/orca-agentinstruct-1M-v1, "
         "code split):\n" + body + "\n"
         "Pattern: an instruction written for an AI coding agent and the "
         "agent-style answer — plans, file edits, commands, verification. "
         "Use as a template for how a coding agent structures a turn: "
         "understand, plan, act, verify.")
    return t if len(t) >= MIN_DOC else None


def doc_reasoning(row):
    """OpenCodeReasoning: input, chain-of-thought output, solution."""
    inp = clip(row.get("input"), 600)
    out = clip(row.get("output"), 1800)
    sol = clip(row.get("solution"), 900)
    diff = clip(row.get("difficulty"), 30)
    if not inp or not out:
        return None
    t = ("CODE REASONING TRACE (nvidia/OpenCodeReasoning"
         + (f", difficulty={diff}" if diff else "") + "):\n"
         f"PROBLEM: {inp}\nREASONING: {out}\nSOLUTION: {sol}\n"
         "Pattern: think-before-code — the trace explores approaches, edge "
         "cases and tests before committing to the final implementation. "
         "Code agents should produce this reasoning internally on hard "
         "problems, then emit the compact solution.")
    return t if len(t) >= MIN_DOC else None


def doc_instruct(row):
    """OpenCodeInstruct: input/output pair with unit tests."""
    inp = clip(row.get("input"), 700)
    out = clip(row.get("output"), 1200)
    tests = clip(row.get("unit_tests"), 700)
    if not inp or not out:
        return None
    t = ("CODE INSTRUCTION PAIR + TESTS (nvidia/OpenCodeInstruct):\n"
         f"TASK: {inp}\nSOLUTION: {out}\nTESTS: {tests}\n"
         "Pattern: every generated solution ships with unit tests — the "
         "verify-by-tests loop. Mirror of the SDK's own conformance model: "
         "golden fixture + assertion, deterministic, no live model needed.")
    return t if len(t) >= MIN_DOC else None


def doc_swe(row):
    """SWE-Gym: issue -> patch workflow."""
    prob = clip(row.get("problem_statement"), 1200)
    patch = clip(row.get("patch"), 1200)
    hints = clip(row.get("hints_text"), 400)
    repo = clip(row.get("repo"), 80)
    ftp = clip(row.get("FAIL_TO_PASS"), 300)
    if not prob or not patch:
        return None
    t = ("AGENT CODING WORKFLOW (SWE-Gym"
         + (f", repo={repo}" if repo else "") + "):\n"
         f"ISSUE: {prob}\nHINTS: {hints}\nPATCH: {patch}\n"
         f"TESTS THAT MUST FLIP: {ftp}\n"
         "Pattern: the reproduce-patch-verify loop — read the issue, "
         "reproduce, write the minimal patch, run FAIL_TO_PASS and "
         "PASS_TO_PASS. This is the canonical workflow a code agent runs "
         "against a repo.")
    return t if len(t) >= MIN_DOC else None


DATASETS = [
    {"id": "glaiveai/glaive-function-calling-v2", "cfg": "default",
     "split": "train", "fn": doc_toolcall},
    {"id": "microsoft/orca-agentinstruct-1M-v1", "cfg": "default",
     "split": "code_", "fn": doc_orca},
    {"id": "nvidia/OpenCodeReasoning", "cfg": "split_0",
     "split": "split_0", "fn": doc_reasoning},
    {"id": "nvidia/OpenCodeInstruct", "cfg": "train",
     "split": "train", "fn": doc_instruct},
    {"id": "SWE-Gym/SWE-Gym", "cfg": "default",
     "split": "train", "fn": doc_swe},
]


def main():
    os.makedirs(KNOW, exist_ok=True)
    docs = repo_docs()
    print(f"[repo] {len(docs)} hand-written SDK docs", flush=True)
    notes, skipped = {}, {}
    for cfg in DATASETS:
        ds_id = cfg["id"]
        avail = dataset_exists(ds_id)
        if not avail:
            skipped[ds_id] = "not served by datasets-server"
            notes[ds_id] = {"status": "skipped", "rows": 0,
                            "note": "not served by datasets-server"}
            print(f"[{ds_id}] skipped: not served", flush=True)
            continue
        cfg_name = cfg.get("cfg") or avail[0][0]
        split = cfg.get("split") or avail[0][1]
        if not any(c == cfg_name and s == split for c, s in avail):
            cfg_name, split = avail[0]
            print(f"[{ds_id}] config substituted -> {cfg_name}/{split}",
                  flush=True)
        try:
            rows = fetch_rows(ds_id, cfg_name, split, ROWS_PER_DS)
        except Exception as e:
            notes[ds_id] = {"status": "skipped", "rows": 0,
                            "note": f"/rows failed: {str(e)[:80]}"}
            print(f"[{ds_id}] skipped: {e}", flush=True)
            continue
        n = 0
        for row in rows:
            if n >= ROWS_PER_DS:
                break
            try:
                t = cfg["fn"](row)
            except Exception:
                continue
            if not t or len(t) < MIN_DOC:
                continue
            if len(t) > MAX_DOC:
                t = t[:MAX_DOC] + "…"
            docs.append({"agent_id": LANE, "dataset": ds_id, "text": t})
            n += 1
        notes[ds_id] = {"status": "ok", "rows": n,
                        "note": f"{cfg_name}/{split}"}
        print(f"[{ds_id}] {n} docs", flush=True)

    out = os.path.join(KNOW, f"{LANE}.jsonl")
    with open(out, "w") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    manifest_path = os.path.join(KNOW, "manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    manifest["muse-code-sdk"] = {
        "docs": {LANE: len(docs)},
        "datasets": {LANE: notes},
        "skipped": skipped,
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    n = build_index()
    print(f"lane {LANE}: {len(docs)} docs; index now holds {n} docs total",
          flush=True)


if __name__ == "__main__":
    main()
