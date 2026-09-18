#!/usr/bin/env python3
"""Ingest music-production datasets from Hugging Face.

Lane: music-production. Additive to the shared FTS5 index.

Proven transport: curl through the egress proxy to datasets-server
/parquet (verify) and /rows (fetch). huggingface_hub is broken here
(urllib can't parse the proxy URL), so everything goes through curl.

Datasets (all verified served, ungated):
  dvilasuero/Electronic_Music_Composition     per-track composition notes:
                                             tempo, drum patterns, bass note
                                             sequences, lead melodies (the gold)
  yatin-superintelligence/Audio-Video-        real music-producer mixing Qs
    Engineering-Agentic-Tasks-1M             (sidechain, snare transients,
                                             low-end muddiness)
  Musictheory94/Chordonomicon                chord sequences w/ section tags
                                             (<verse_1>, <chorus_1>), genre/decade
  pacoreyes/electronic-music-wikipedia-rag    wikipedia chunks on electronic
                                             artists/genres (title, tags, article)
  m-a-p/MusicTheoryBench                     music-theory Q/A with analysis
                                             (stem, options, answer, analysis)

Usage: python3 train/ingest_music.py
"""
import json, os, re, sys
from collections import Counter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "train"))
from ingest import dataset_exists, fetch_rows, build_index  # noqa: E402

KNOW = os.path.join(BASE, "knowledge")

MIN_DOC = 100
MAX_DOC = 3000


def clip(v, n):
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:n]


# ------------------------------------------------------------ Electronic_Music_Composition
# Row shape: track_name (composition notes — tempo, drum patterns, bass note
# sequences, lead melodies — THIS is the gold), kimi-k2 / qwen-coder-3 (huge
# HTML page strings — ignored entirely). Docs built from track_name only,
# prefixed with the track name.

def doc_emc(row):
    notes = clip(row.get("track_name"), 2600)
    if not notes:
        return None
    t = ("ELECTRONIC MUSIC COMPOSITION NOTES (track notes: tempo, drum "
         "patterns, bass note sequences, lead melodies)\n"
         f"{notes}\n"
         "Pattern: a full arrangement spec — tempo/key, per-section drum "
         "programming (kick/snare/hat placement), bass note sequences with "
         "rhythm values, and monophonic lead lines bar by bar.")
    return t if len(t) >= MIN_DOC else None


# ------------------------------------------------------------ Audio-Video-Engineering-Agentic-Tasks-1M
# Row shape: professional, group, user_prompt (a producer/beat maker asking
# for mixing help). Prefer rows where group == "Music Production".

def doc_av(row):
    prof = clip(row.get("professional"), 60) or "Music Producer"
    prompt = clip(row.get("user_prompt"), 2200)
    if not prompt:
        return None
    t = (f"MIXING/PRODUCTION QUESTION from a {prof}:\n{prompt}\n"
         "Context: real producer question about mixing/production technique "
         "— sidechain compression, snare transients, low-end muddiness, "
         "EQ carving, stereo width.")
    return t if len(t) >= MIN_DOC else None


# ------------------------------------------------------------ Chordonomicon
# Row shape: chords (full sequence w/ section tags), genres, main_genre, decade.

def doc_chord(row):
    chords = clip(row.get("chords"), 800)
    if not chords:
        return None
    genre = clip(row.get("main_genre"), 40) or "unknown"
    decade = clip(row.get("decade"), 10) or "unknown"
    genres = clip(row.get("genres"), 200)
    t = (f"CHORD PROGRESSION ({genre}, {decade}):\n{chords}\n"
         f"GENRES: {genres}\n"
         "Pattern: chord sequence tagged per song section "
         "(<intro_1>, <verse_1>, <chorus_1>, <solo_1>); "
         "use as arrangement-aware progression templates.")
    return t if len(t) >= MIN_DOC else None


# ------------------------------------------------------------ electronic-music-wikipedia-rag
# Row shape: metadata (title, tags, similar_artists, genres), article
# (wikipedia chunk about an electronic artist/genre).

def doc_wiki(row):
    meta = row.get("metadata") or {}
    title = clip(meta.get("title") or meta.get("artist_name"), 80)
    tags = clip(meta.get("tags") or meta.get("genres"), 220)
    article = clip(row.get("article"), 1000)
    if not article:
        return None
    t = (f"ARTIST/GENRE REFERENCE: {title} [{tags}]\n{article}\n"
         "Context: encyclopedic background on an electronic artist or genre "
         "— production style, era, influences.")
    return t if len(t) >= MIN_DOC else None


# ------------------------------------------------------------ MusicTheoryBench
# Row shape: stem (question), options (dict A-D), answer, analysis.

def doc_theory(row):
    stem = clip(row.get("stem"), 600)
    answer = clip(row.get("answer"), 20)
    analysis = clip(row.get("analysis"), 1600)
    if not stem or not answer:
        return None
    options = clip(row.get("options"), 600)
    t = (f"MUSIC THEORY Q/A (m-a-p/MusicTheoryBench):\n"
         f"Q: {stem}\nOPTIONS: {options}\nA: {answer}: {analysis}\n"
         "Context: theory question with the correct answer and explanation "
         "— harmony, rhythm, form, acoustics, pedagogy.")
    return t if len(t) >= MIN_DOC else None


# ------------------------------------------------------------ main

LANE = "music-production"

DATASETS = [
    {"id": "dvilasuero/Electronic_Music_Composition", "rows": 200,
     "cfg": "default", "split": "train", "fn": doc_emc},
    {"id": "yatin-superintelligence/Audio-Video-Engineering-Agentic-Tasks-1M",
     # dataset is ~1M rows with mixed groups; fetch 2000 so the
     # "Music Production" group filter still yields ~200 docs
     "rows": 2000, "cfg": "default", "split": "train", "fn": doc_av,
     "group_filter": "Music Production"},
    {"id": "Musictheory94/Chordonomicon", "rows": 200,
     "cfg": "default", "split": "train", "fn": doc_chord},
    {"id": "pacoreyes/electronic-music-wikipedia-rag", "rows": 200,
     "cfg": "default", "split": "train", "fn": doc_wiki},
    {"id": "m-a-p/MusicTheoryBench", "rows": 200,
     "cfg": "default", "split": "test", "fn": doc_theory},
]


def main():
    os.makedirs(KNOW, exist_ok=True)
    docs, notes, skipped = [], {}, {}
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
        try:
            rows = fetch_rows(ds_id, cfg_name, split, cfg["rows"])
        except Exception as e:
            notes[ds_id] = {"status": "skipped", "rows": 0,
                            "note": f"/rows failed: {str(e)[:80]}"}
            print(f"[{ds_id}] skipped: {e}", flush=True)
            continue
        group_filter = cfg.get("group_filter")
        n = 0
        for row in rows:
            if n >= 200:
                break
            if group_filter and row.get("group") != group_filter:
                continue
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
                        "note": f"{cfg_name}/{split}"
                        + (f", group={group_filter}" if group_filter else "")}
        print(f"[{ds_id}] {n} docs", flush=True)

    out = os.path.join(KNOW, "music-production.jsonl")
    with open(out, "w") as f:
        for d in docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")

    manifest_path = os.path.join(KNOW, "manifest.json")
    manifest = json.load(open(manifest_path)) if os.path.exists(manifest_path) else {}
    manifest["music"] = {
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
