# Acceptance criteria — Provenance Guard

Five criteria that say what "working" means for this service, written in unit 7
**before** you built it.

**All five are yours.** None are given.

An acceptance criterion names a number or something plainly observable. *"The
detector is accurate"* is an opinion — and perfect AI detection isn't possible
anyway, so it's an opinion about something nobody can deliver. *"Of 10 pieces I
wrote myself, at most 1 is labelled high-confidence AI"* is a criterion.

Under each, write a sentence or two on **why that target**. *"I allow at most 1
false positive in 10 because on a writing site a wrong accusation costs more
than a missed detection"* is a real answer.

> Missing your own targets next unit costs you nothing. Setting a target so
> easy you can't miss it does.

---

## Pick numbers you can defend

**Cover at least three of these five areas.** They're prompts, not a form.

| Area | A question it could answer |
|---|---|
| False positives | How often may a human's writing get called AI? |
| Score spread | How far apart should clearly-AI and clearly-human text score? |
| Label coverage | Is every one of your three labels actually reachable? |
| The appeal path | Does an appeal always change status and always get recorded? |
| Bad input | What happens when `text` is missing, empty, or enormous? |

Two things worth knowing before you pick numbers:

- **The expensive mistake is one-sided.** Missing some AI text costs the site a
  little. Accusing a real writer costs that person a lot. A criterion that
  treats both errors as equally bad is describing a system nobody would ship.
- **Unit 8 tests across three trials, and the target has to hold across all
  three.** Your first signal runs a model, so identical input can score
  differently twice. A target of "at most 1 in 10" against trials of 2, 1, 2 is
  a **miss**.

---
## 1. Plain human writing is rarely accused

Of 10 plain-written human texts (by non-native or beginner writers), at most 1 is labelled high-confidence AI.
This must hold in each of three trials, not on average.

**How I'll check it:** submit all 10 to `/submit` and count `guess == "ai"`.

**Why this target:** A wrongly accused writer loses trust in the site and has
little room to argue back. A missed AI text costs the site much less. This is
deliberately stricter than criterion 3, which allows more "unsure" results,
because "unsure" is not an accusation.

---

## 2. Clearly-AI and clearly-human text score far apart

The combined score of `samples/clearly_ai.json` minus the combined score of
`samples/clearly_human.json` is at least 0.35 in each of three trials.

**How I'll check it:** read both combined scores from the audit log.

**Why this target:** My thresholds are 0.35 and 0.65, so a gap of 0.30 is the
bare minimum to land in opposite labels, with no slack. Signal one alone gave
0.31, so a 0.35 target forces signal two to help instead of hurt.

---

## 3. The human label can actually fire

Of 10 human texts in an expressive, varied voice (like `clearly_human.json`),
at least 5 are labelled high-confidence human in each of three trials.

**How I'll check it:** submit all 10 and count `guess == "human"`.

**Why this target:** If the human label almost never appears, the service only
ever says "unsure", which is useless to the site. The bar is lower than
criterion 1 on purpose: a text stuck in "unsure" is a small cost, while a
wrong accusation is a large one. I expect this to be hard, because my human
sample scored 0.4445 on signal one alone, above the 0.35 human threshold.

---

## 4. Bad input never causes a 500

Each of these 10 inputs to `/submit` returns the status in my API contract,
and none returns 500, in each of three trials:

| Input | Expected status |
|---|---|
| `text` missing | 400 |
| `text` empty string | 400 |
| `text` whitespace only | 400 |
| `text` is a number | 400 |
| 9 words | 400 |
| exactly 10 words | 200 |
| 3000 characters | 200 |
| 3001 characters | 413 |
| body is a bare JSON list | 400 |
| body is not valid JSON | 400 |

**How I'll check it:** a script that sends each input and compares the status.

**Why this target:** A crash on malformed input is one of the most common real
failures, and a 500 tells the caller nothing about what to fix. Listing the
inputs makes it impossible to pass by testing only the easy ones.

---

## 5. An appeal always changes status and is always recorded

Across 3 cases, in each of three trials:
- A valid `content_id` returns 200 with status `under_review`, and exactly one
  new `event: "appeal"` entry appears in the log.
- A nonexistent `content_id` returns 404, and no appeal entry is written.
- A second appeal on the same `content_id` returns 409, and no extra appeal
  entry is written.

**How I'll check it:** call `/appeal`, then read `/log` and count entries.

**Why this target:** `/appeal` is the only thing between a wrong accusation
and nothing at all. If an appeal is silently lost, the writer has no recourse
and I can't audit it.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     UNIT 8 — read this before you change anything above.

     If a criterion turns out to be BROKEN rather than merely unmet, you can
     revise it, and that earns credit. But never delete or edit the original
     line. Add the revision underneath, like this:

         ## 2. Uncertain cases land in the unsure band

         The system handles uncertain cases well.

         **Why this target:** ...

         > **Revised in unit 8:** Text I judged borderline scores between
         > 0.4 and 0.6 in at least 4 of 5 cases.
         >
         > **Why revised:** "well" gave me nothing to check. I couldn't
         > reach a verdict from it at all.

     That's a revision because the criterion couldn't be MEASURED.

     Lowering a target because you missed it is not a revision, and it costs
     you the point:

         ✗ "At most 1 of 10 of my own pieces flagged as AI" → "at most 3
            of 10", because 1 of 10 turned out to be hard.

     A number you missed stays where it is, gets diagnosed, and gets a fix
     attempted. That's where the points are.
     ───────────────────────────────────────────────────────────────────────── -->
