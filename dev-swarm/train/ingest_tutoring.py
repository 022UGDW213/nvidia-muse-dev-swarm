#!/usr/bin/env python3
"""Ingest e-learning / tutoring datasets from Hugging Face.

Lane: elearning-tutoring. Additive to the shared FTS5 index.

Proven transport: curl through the egress proxy to datasets-server
/parquet (verify) and /rows (fetch). huggingface_hub is broken here
(urllib can't parse the proxy URL), so everything goes via curl.

Datasets (all verified served, ungated):
  princeton-nlp/TutorChat                          tutor-student dialogues
  Eedi/Question-Anchored-Tutoring-Dialogues-2k     question-anchored dialogues
                                                   with tutor talk-move labels
  knght0wl21/socratic-tutoring-dataset             socratic tutoring cases
  derek-thomas/squad-v1.1-t5-question-generation   passage -> quiz questions

Usage: python3 train/ingest_tutoring.py
"""
import json, os, re, sys
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "train"))
from ingest import dataset_exists, fetch_rows, build_index  # noqa: E402

KNOW = os.path.join(BASE, "knowledge")

MIN_DOC = 100
MAX_DOC = 3000

TALK_MOVES = Counter()


def clip(v, n):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]


# ------------------------------------------------------------ TutorChat

def doc_tutorchat(row):
    turns = row.get("conversation") or []
    if not turns:
        return None
    topic = clip(turns[0], 220)
    lines = [f"TUTORING DIALOGUE (TutorChat, mode={clip(row.get('mode'), 20)})",
             f"TOPIC: {topic}"]
    speaker = "STUDENT"  # names like studentstart_* => student opens
    for t in turns[1:7]:
        txt = clip(t, 600)
        if txt:
            lines.append(f"{speaker}: {txt}")
        speaker = "TUTOR" if speaker == "STUDENT" else "STUDENT"
    lines.append("Pattern: tutor answers with explanations, then follows up; "
                 "student asks clarifying questions turn by turn.")
    t = "\n".join(lines)
    return t if len(t) >= MIN_DOC else None


# ------------------------------------------------------------ Socratic

def doc_socratic(row):
    t = (f"SOCRATIC TUTORING CASE (scenario {row.get('scenario')})\n"
         f"QUESTION: {clip(row.get('question'), 400)}\n"
         f"STUDENT'S INCORRECT SOLUTION: "
         f"{clip(row.get('student_incorrect_solution'), 600)}\n"
         f"STUDENT PROFILE: {clip(row.get('student_profile'), 200)}\n"
         f"TEACHER READ OF CONFUSION: "
         f"{clip(row.get('teacher_described_confusion'), 200)}\n"
         f"DIALOGUE:\n{clip(row.get('conversation'), 1200)}\n"
         "Pattern: the tutor never hands over the answer; it probes the "
         "misconception with targeted questions until the student self-corrects.")
    return t if len(t) >= MIN_DOC else None


# ------------------------------------------------------------ SQuAD question generation

def doc_squadqg(row):
    t = (f"QUESTION GENERATION PAIR\n"
         f"CONTEXT: {clip(row.get('context'), 900)}\n"
         f"GENERATED QUESTIONS: {clip(row.get('questions'), 700)}\n"
         "Pattern: factual quiz questions generated from a passage — "
         "training signal for auto-generating quiz questions from course content.")
    return t if len(t) >= MIN_DOC else None


# ------------------------------------------------------------ Eedi (message rows -> dialogues)

def clean_move(m):
    if not m:
        return None
    m = str(m).strip()
    if m.lower() in ("none", "<none>", "null", ""):
        return None
    TALK_MOVES[m] += 1
    return m


def doc_eedi(iid, qid, qtext, turns):
    lines = [f"QUESTION-ANCHORED TUTORING DIALOGUE (intervention {iid}, "
             f"question {qid})"]
    if qtext:
        lines.append(f"ANCHOR QUESTION: {clip(qtext, 400)}")
    for seq, who, move, text in sorted(turns):
        tag = f"TUTOR[{move}]" if (who == "TUTOR" and move) else who
        lines.append(f"{tag}: {clip(text, 500)}")
    lines.append("Pattern: tutor talk moves are labeled per turn "
                 "(e.g. probing, scaffolding); the dialogue stays anchored "
                 "to one specific question.")
    t = "\n".join(lines)
    return t if len(t) >= MIN_DOC else None


def ingest_eedi():
    ds_id = "Eedi/Question-Anchored-Tutoring-Dialogues-2k"
    avail = dataset_exists(ds_id)
    if not avail:
        return [], {ds_id: {"status": "skipped", "rows": 0,
                            "note": "not served by datasets-server"}}
    # question text lookup
    qmap = {}
    try:
        meta = fetch_rows(ds_id, "dq-question-metadata", "train", 400)
        for row in meta:
            if str(row.get("Label")) == "Question Text" and row.get("Text"):
                qmap[row.get("QuestionId_DQ")] = row["Text"]
    except Exception as e:
        print(f"[eedi metadata] {e}", flush=True)
    rows = fetch_rows(ds_id, "anchored-dialogues", "train", 5000)
    groups = {}
    for row in rows:
        iid = row.get("InterventionId")
        if iid is None:
            continue
        g = groups.setdefault(iid, {"qid": row.get("QuestionId_DQ"), "turns": []})
        move = clean_move(row.get("TalkMovePrediction"))
        who = "TUTOR" if row.get("IsTutor") else "STUDENT"
        g["turns"].append((row.get("MessageSequence") or 0, who, move,
                           row.get("MessageString") or ""))
    docs, n = [], 0
    for iid, g in groups.items():
        if n >= 150:
            break
        t = doc_eedi(iid, g["qid"], qmap.get(g["qid"]), g["turns"])
        if not t:
            continue
        if len(t) > MAX_DOC:
            t = t[:MAX_DOC] + "…"
        docs.append({"agent_id": "elearning-tutoring", "dataset": ds_id,
                     "text": t})
        n += 1
    print(f"[{ds_id}] {n} dialogues from {len(rows)} message rows", flush=True)
    return docs, {ds_id: {"status": "ok", "rows": n,
                          "note": "anchored-dialogues/train (grouped by InterventionId)"}}


# ------------------------------------------------------------ main

LANES = [
    ("elearning-tutoring", [
        {"id": "princeton-nlp/TutorChat", "rows": 150, "fn": doc_tutorchat},
        {"id": "knght0wl21/socratic-tutoring-dataset", "rows": 150,
         "cfg": "default", "split": "train", "fn": doc_socratic},
        {"id": "derek-thomas/squad-v1.1-t5-question-generation", "rows": 150,
         "fn": doc_squadqg},
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
        # Eedi needs message-row grouping
        eedi_docs, eedi_notes = ingest_eedi()
        docs.extend(eedi_docs)
        notes.update(eedi_notes)
        out = os.path.join(KNOW, "elearning-tutoring.jsonl")
        with open(out, "w") as f:
            for d in docs:
                f.write(json.dumps(d, ensure_ascii=False) + "\n")
        all_notes[lane] = notes
        stats[lane] = len(docs)

    manifest_path = os.path.join(KNOW, "manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    manifest["tutoring"] = {
        "docs": dict(stats),
        "datasets": all_notes,
        "skipped": {},
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    n = build_index()
    print(f"lanes: {dict(stats)}; index now holds {n} docs total", flush=True)
    print("TALK MOVES:", dict(TALK_MOVES.most_common(15)), flush=True)


if __name__ == "__main__":
    main()
