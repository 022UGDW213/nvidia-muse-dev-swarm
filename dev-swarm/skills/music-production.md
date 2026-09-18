# Music Production Skill

Runbook for composing and producing electronic tracks. Grounded in 810 HF docs
across 5 datasets, FTS-queryable from the shared index (`agent_id = 'music-production'`):

| Dataset | Docs | What it contributes |
|---|---|---|
| `dvilasuero/Electronic_Music_Composition` | 10 | Full per-track composition notes: tempo, drum placement, bass note sequences with rhythm values, monophonic lead lines bar by bar, pad triads, pluck arpeggios (HTML junk columns ignored) |
| `yatin-superintelligence/Audio-Video-Engineering-Agentic-Tasks-1M` | 200 | Real Music Producer / Beat Maker / DJ Producer mixing questions (`group == "Music Production"`): sidechain compression, low-end muddiness, snare transients, 2kHz harshness, stereo vs mono sub |
| `Musictheory94/Chordonomicon` | 200 | Chord sequences tagged per song section (`<intro_1>`, `<verse_1>`, `<chorus_1>`, …) with main genre / decade |
| `pacoreyes/electronic-music-wikipedia-rag` | 200 | Artist/genre encyclopedia chunks: title + tags + article lead (techno 45 docs, trance 34, trip-hop/downtempo well covered) |
| `m-a-p/MusicTheoryBench` | 200 | Theory Q/A with explanations: chords, scales, intervals, key signatures (plus some instrument/pedagogy rows) |

Index queries: `SELECT text FROM docs WHERE agent_id='music-production' AND docs MATCH '<terms>'`.

## The composition cell (your reusable unit — from EMC docs)

The Electronic_Music_Composition notes all follow one pattern; steal it as your
per-section template:

1. **Tempo + meter** (e.g. 128 bpm, 4/4)
2. **Drums as placements**: kick on 1, 2+, 3, 4+; snare on 2 & 4; closed-hat 8ths — write every element as "which beats", not vibes
3. **Bass as a note sequence with rhythm values**: `F2-G2-A♭2-C3`, each note dotted-eighth + rest sixteenth, octave jump on the C3. One concrete bass cell with a rhythmic gimmick beats a wall of notes.
4. **Lead as bar-by-bar monophonic lines** (rhythm values per bar: dotted-eighth, rest sixteenth, eighths…)
5. **Pad**: triads, 2-bar loop, whole notes (e.g. F maj → G min → A♭ maj → C maj)
6. **Pluck arpeggio**: 16ths cycling chord tones (e.g. F3-C4-A4-C4)

Compose every section of every track in this exact six-line format. It is the
fastest path from idea to a finished arrangement.

## Dubstep drop construction

- **Half-time drums**: the groove reads at ~70 BPM while the project runs 140.
  Kick on 1, snare on 3 (the half-time backbeat), hats in 8ths/16ths for the
  rolling feel. Per the EMC template, write placements first.
- **Wobble/growl bass design**: a saw/square bass through a low-pass filter
  with an **LFO on the cutoff** — rate synced (1/8 or 1/4 notes), depth to
  taste. Automate LFO rate and filter depth across the drop (slower/deeper on
  the last 4 bars). Layer a detuned growl (two saws ±10 cents) on top of a
  clean sine **sub** playing the same root — sub always mono, always clean.
- **Drop call-and-response**: bass phrase (2 bars) answered by a drum fill or
  vocal chop (2 bars). Vary the wobble pattern each 4 bars — repetition with
  mutation, never copy-paste.
- Wiki docs on dubstep's lineage (UK garage / 2-step roots) are thin in this
  corpus — lean on the bass-design pattern above instead.

## Techno arrangement (DJ-friendly)

- **Rolling bassline**: off-beat 16th or 8th ostinato on the root (e.g. F1-F1-F1-F1
  with velocity accents on the off-beats), locked to a 4-on-the-floor kick.
  EMC bass cells transfer directly: short note + short rest + octave jump =
  instant drive.
- **Dub chord stabs**: minor/major triad stabs on the off-beat (the "and" of 2
  and 4), drenched in dotted-1/8 delay + plate reverb, low-passed so they sit
  under the hats. Use the pad triads from the EMC template as stab source
  material.
- **Filter sweeps**: one high-pass sweep over 8–16 bars into the drop, one
  low-pass sweep out. Automate, don't redraw by hand each time.
- **DJ-friendly intro/outro**: 16–32 bars of drums + bass only (no melodic
  content) at both ends so the track mixes in/out. Structure:
  `intro (32) → groove A (32) → break (16) → groove B/drop (32) → break (16)
  → groove C (32) → outro (32)`. The wiki-rag techno docs (45) confirm the
  Detroit/Berlin lineage: repetition with subtle mutation, not verse-chorus.

## Trance (supersaws, builds, breakdowns)

- **Supersaw stacking**: 5–9 detuned saws (±15–25 cents) per note, chord
  voicings in octaves. High-pass the stack at ~150 Hz so it never fights the
  sub; sidechain it to the kick (see mixing).
- **Emotional progressions**: pull minor-key loops from the Chordonomicon docs —
  e.g. `Csmin A Csmin A Csmin A Csmin A B` (i–VI–i–VI–…–VII in C# minor).
  Trance lives on i–VI–III–VII and i–VII–VI–VII; keep the chorus progression
  to 4 chords max so the supersaw stack stays intelligible.
- **Breakdown**: strip to pad + arpeggio + vocal/atmo for 16–32 bars, low-pass
  opening slowly. **Build**: snare roll (16ths → 32nds), riser, filter opening,
  kick re-introduced on the "1" of the drop with a 1-bar drum fill before it.
  Never let the build exceed 32 bars.
- Wiki-rag trance docs (34) cover the euphoric/uplifting lineage — match the
  arrangement to it: long breakdown, single cathartic drop.

## Electronic music theory (from Chordonomicon + MusicTheoryBench)

- **Minor-key workhorse**: `i – VI – III – VII` (e.g. Am – F – C – G).
  Dark variant straight from the corpus: `Csmin – A – B` (i–VI–VII), looped
  under a half-time drop. The VII→i resolution gives tension without the
  cheesiness of a full V–i.
- **Section-aware progressions**: Chordonomicon rows tag chords per section —
  verse progressions stay diatonic and sparse (`F C E7 Amin…`), choruses add
  the 7ths and the lift (`…G D G D A D…`). Copy that discipline: verse = roots
  + triads, chorus = extensions + busier rhythm.
- **Tension/release**: secondary dominants (E7→Am in C major rows) before a
  chorus; in minor, raise the 7th (G# in A minor) for a harmonic-minor lift
  into the drop, then drop it back to natural minor for the verse.
- **Arpeggios as accompaniment**: MusicTheoryBench confirms the textbook
  definition — chords played note-by-note. Your 16th pluck arpeggios (EMC
  template step 6) are exactly this; cycle chord tones, octave-displace the
  top note for movement.
- Watch out: MusicTheoryBench `test` rows mix real theory (chords, scales,
  intervals — ~30 docs) with pedagogy/instrument-care rows; trust the
  Chordonomicon progressions for compositional choices, the Bench for
  terminology checks.

## Mixing / mastering basics (from the 200 producer Q docs)

- **Sidechain compression**: kick ducks the bass (and the supersaw stack).
  Fast attack, release timed to the groove (~1/4 note), 2–4 dB of gain
  reduction — the single most-asked technique in the corpus. If the low end is
  muddy, sidechain first, EQ second.
- **Stereo width vs mono sub**: keep everything below ~120 Hz mono (kick, sub
  bass). Width lives in the mids/highs: hats, stabs, pads, reverbs. 98 corpus
  docs discuss mono/sub handling — collapsing the sub to mono is the consensus
  fix for weak low end on club systems.
- **EQ carving**: the recurring complaint is harshness around **2 kHz**
  (snares, leads). Cut 2–3 dB with a medium Q on the offending element rather
  than boosting elsewhere; high-pass non-bass elements to clear mud.
- **Snare transients**: if the snare feels stiff/lifeless, shorten the sample
  start, add a transient shaper (+attack), and layer a clap slightly late
  (5–15 ms) for width — don't just add overdrive.
- **Limiter on the master**: last in chain, 1–3 dB of gain reduction max.
  If you need more, the mix isn't done — go back to sidechain and EQ.

## Working method (for the track-builder)

1. Pick genre → key → tempo. 2. Write the six-line composition cell for the
   verse and the drop (EMC template). 3. Pull a progression from Chordonomicon
   (minor: i–VI–VII or i–VI–III–VII). 4. Arrange: DJ intro/outro if techno,
   half-time drop if dubstep, breakdown/build if trance. 5. Mix pass:
   sidechain → mono sub → carve 2 kHz → limiter. Query the index when stuck:
   `docs MATCH 'sidechain bass kick'` etc. with `agent_id='music-production'`.
