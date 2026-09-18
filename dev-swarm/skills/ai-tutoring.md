# AI Tutoring Skill

Runbook for building AI tutors and study assistants. Grounded in 588 HF docs:
`princeton-nlp/TutorChat` (150), `Eedi/Question-Anchored-Tutoring-Dialogues-2k`
(138), `knght0wl21/socratic-tutoring-dataset` (150),
`derek-thomas/squad-v1.1-t5-question-generation` (150).

## The tutor loop (from the corpora)

Every working tutoring session follows this loop — Eedi, Socratic, and
TutorChat all converge on it:

1. **Anchor** — one question or topic per session. Load the anchor into
   context first (Eedi dialogues never drift off their `QuestionId_DQ`).
2. **Diagnose** — before responding, name the student's misconception to
   yourself (the `teacher_described_confusion` field in the socratic corpus
   exists for exactly this).
3. **Probe, don't tell** — ask the question that exposes the misconception.
   The socratic rule is absolute: the tutor never hands over the answer.
4. **Press for accuracy** — the #1 labeled tutor move (624/1,224 Eedi tutor
   turns): "what exactly do you mean by…", "can you say that more precisely".
   Precision-first beats explanation-first.
5. **Revoice** — restate their idea back, slightly cleaned up (189 turns):
   "so you're saying…". It validates and sharpens in one move.
6. **Check alignment** — `<Keep Together>` (376 turns): confirm you're on the
   same page before advancing. In 1:1, that's "does that make sense so far?".

## Talk-move cheat sheet

| Move | When to use | Corpus weight |
|---|---|---|
| Press for Accuracy | student is vague or hand-wavy | 624 — default |
| Keep Together | transitioning topics, checking alignment | 376 |
| Revoicing | student has the right idea, poorly stated | 189 |
| Press for Reasoning | student is right — ask *why* | 16 — depth push |
| Getting Student to Relate | connect to prior knowledge | 17 |
| Restating | echo for emphasis | 2 — rare |

Most turns need no labeled move — scaffolding, encouragement, logistics.
Moves are deliberate interventions, not filler.

## Socratic case format (for training/eval data)

Structure every tutoring case as the corpus does:

```
QUESTION: <the problem>
STUDENT'S INCORRECT SOLUTION: <their wrong attempt, verbatim>
STUDENT PROFILE: <one line — adapt tone, not content>
TEACHER READ OF CONFUSION: <name the misconception first>
DIALOGUE: <probe until self-correction>
```

Self-correction is the success metric, not answer delivery.

## TutorChat dialogue shape (openbook mode)

- Tutor opens with the topic + skills to develop (one short block).
- Then the student drives: short clarifying questions, tutor answers with
  real explanations (400–2,000 chars). Don't lecture in a fixed order —
  follow the student's curiosity.
- Student enthusiasm ("I'm really intrigued by…") is the signal to go
  deeper, not to move on.

## Quiz generation from course content

The SQuAD question-generation pairs give the recipe:

1. Take a content block (≤900 chars — one module section, not a chapter).
2. Extract entities and relations (who/what/when/why), not opinions.
3. Emit factual questions whose answers are in the text.
4. One anchor per quiz item — same anchoring discipline as tutoring.

This is the training signal for auto-generating quizzes from LMS modules:
passage in, questions out. Validate by checking each generated question is
answerable from its source passage.

## Wiring into a study assistant (e.g. an LMS)

- **System prompt:** encode the tutor loop (anchor → diagnose → probe →
  press for accuracy). Forbid direct answer-giving on first contact with a
  misconception — one probe first.
- **Retrieval:** index the tutoring corpus (or your course content) and
  retrieve anchor-relevant examples before responding — same pattern as the
  dev-swarm `skill_context` (top-3 FTS hits attached per task).
- **Session state:** keep the anchor question pinned in context for the whole
  session; re-anchor if the student drifts.
- **Eval:** score sessions on self-correction rate and anchor adherence,
  not on answer correctness alone.
