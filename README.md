# Provenance Guard

> ### 👋 Start here
>
> **New to this repo? Read [RUNNING.md](RUNNING.md) first.**
>
> Once `python test.py` passes, in one terminal:
>
> ```bash
> python app.py
> ```
>
> and in another:
>
> ```bash
> curl -X POST http://127.0.0.1:5000/ping \
>   -H "Content-Type: application/json" \
>   -d '{"message": "hello"}'
> ```
>
> That's a web service. Something sent it text and it sent something back.
> Everything this unit is filling in the middle.
>
> **The rest of this file is your submission.** Fill it in as you go.

---

<!-- ─────────────────────────────────────────────────────────────────────────
     Unit 7 asks for the first five sections. Unit 8 adds the five below.

     Everything is pasted as TEXT. A pasted curl response gets full credit;
     a picture of your terminal gets none.
     ───────────────────────────────────────────────────────────────────────── -->

<!-- ═══════════════════════ UNIT 7 — THE BUILD ═══════════════════════ -->

## What This Does

<!-- The path a submission takes, from arriving to the label a reader sees.
     Six or seven steps — this is the trace you wrote in Milestone 1. -->

**Step 1: The route (`app.py::submit`).** Receives a JSON body. Adds a validated
`text`, a `creator_id`, and a new `content_id`. Passes the text to both signals.
Bad input (missing, empty, non-string, or under a minimum word count) is rejected
with a 400 before any signal runs. If the model cannot load
(`DetectorUnavailable`), the route returns a 503. As a backstop, it also turns a
`ValueError` from the detector into a 400.

**Step 2: Signal one (`detector.py::model_signal`).** Receives the text. Adds a
0-1 score for how predictable the text is to a language model (higher = more
AI-like). Returns it to the route.

**Step 3: Signal two (`stylometry.py::style_signal`).** Receives the text. Adds
a 0-1 score for the shape of the text (sentence-length variation, vocabulary
repetition, punctuation), with no regard for meaning (higher = more AI-like).
Returns it to the route.

**Step 4: The combining rule (`scoring.py::combine_signals`).** Receives the two
scores. Adds one combined 0-1 score (higher = more AI-like). Returns it to the
route.

**Step 5: The label mapping (`scoring.py::score_to_label`, plus a confidence
helper in `scoring.py`).** Receives the combined score. Adds a `guess`
("human", "unsure" or "ai"), the plain-English `label` a reader sees, and a
`confidence`, meaning how sure the system is in its own guess. Returns all
three to the route.

**Step 6: Storage (`audit.py::log_decision`).** Receives the content_id,
creator_id, both signal scores, the combined score, the guess, the label and the
confidence. Adds one log line with a timestamp and `status: "decided"`. Returns
to the route. This line is what `/appeal` later finds by content_id.

**Step 7: The response.** The route receives everything decided and adds nothing
new. It sends the client a selected subset: `content_id`, `guess`, `confidence`,
`label`, `model_score` and `style_score`. The combined score and the log entry
stay internal.

---

## Signals and Scoring

<!-- For each signal: what property it measures, why that might differ between
     human and AI writing, and WHAT IT CAN'T SEE.

     The blind spot is not optional. If you can't name it you don't understand
     the signal yet — and unit 8's attack set is built out of blind spots. -->

### Signal one — the model signal

**What it measures:**
It runs a language model (gpt2) over the text and measures how well the model
could predict each word. That "degree of surprise" is perplexity. **Lower**
perplexity means the text is more predictable, so it is treated as more
AI-like. The result is converted to a 0–1 score, where higher means more
AI-like.

**Why that might differ between human and AI writing:**
An AI writes by picking the word that is likely to come next, so its output is
easy for a model to predict. Human writing has surprising word choices and
abrupt turns, so it is harder to predict.

**What it can't see:**
Predictability does not tell us who wrote the text. Real people who write in
plain words and short sentences (someone writing in a second language, a
child, anyone writing plainly on purpose) get AI-like scores, and they are the
people with the least room to argue back. This is measured: Maria, a (fictional) Russian
speaker with three years of English, wrote three plain poems that scored
`model_score` 0.586, 0.599 and 0.604 (perplexity 36.2, 35.0 and 34.6). My
human sample scored 0.4445 and my AI sample 0.7544, so her writing landed well
above the human sample and roughly midway to the AI sample. The starter's notes
say the reverse also happens, that ornate text full of rare words reads as
human; I did not test that. Formal writing does not reliably read as human
either: my formal paragraph scored 0.644. The score is also fragile: five
small edits (three typos, a semicolon, a merged sentence) moved `model_score`
for the AI sample from 0.754 to 0.505, and a trailing newline alone moved
scores by up to 0.025, which is why the route strips `text`.

### Signal two — the style signal

**What it measures:**
The shape of the text, without reading its meaning. It combines two measures,
each mapped to 0–1 and averaged equally: `sentence_length_spread` (standard
deviation of sentence length divided by the mean; even sentences score as
AI-like) and `punctuation_density` (commas, semicolons and dashes per word;
sparse punctuation scores as AI-like). Higher means more AI-like. A third
measure, `type_token_ratio`, is computed but has weight 0 (see below).

**Why that might differ between human and AI writing:**
AI prose tends toward even, mid-length sentences, while human prose is lumpier,
with a short sentence next to a long one. On my samples spread separated them
(AI 0.413, human 1.128). The punctuation direction is a guess that held on one
AI and one human sample. I assumed AI vocabulary would be narrower, but the AI
sample had the higher type-token ratio (0.979 against 0.874), so I gave it
weight 0.

**What it can't see:**
It cannot read, so anything that changes the shape without changing the
substance moves it, and some honest writing has the "AI" shape.
- **Formal human prose.** My own formal paragraph has long, even sentences
  and few commas (spread 0.193, punctuation 0.025). Both measures hit the AI
  end, so style was 1.000 and the combined score 0.822, higher than my
  clearly-AI sample (0.813).
- **Plain writers.** Maria's journey poem has five even lines (spread 0.399),
  almost the same as the AI sample (0.413).
- **Cheap edits.** Five small edits to the AI sample (typos, one semicolon,
  two sentences merged; no content word changed) moved style from 0.871 to
  0.702. Spread rose from 0.413 to 0.486 and punctuation from 0.043 to 0.054
  (the one semicolon). Most of the combined drop (0.813 to 0.603) came from
  signal one.
- **Untested predictions.** Splitting sentences at odd places should raise
  spread, and pasting in a quotation should change sentence lengths. I did not
  run either. Adding commas or dashes should push punctuation toward human
  without changing a word.
- **Line breaks.** I count a newline as a sentence end, so hard-wrapped prose
  is chopped into similar-length pieces and looks more AI-like.
- **Tuned anchors.** The anchors (0.90/0.30 and 0.09/0.04) were chosen from
  six texts, then checked against a seventh that broke them.

### The combining rule

**The rule:**
The combined score is a weighted average of the two signals, with equal
weights. It is not resolved in favour of either signal. When the signals
disagree, the average lands between them, so a strong lean on one side is
softened by the other. I considered stronger rules (raising the AI threshold,
lowering the style weight, capping a saturated style score) and chose to leave
the rule simple and record where it fails. I could not justify any of those
changes from the few texts I have, and each trades missed AI text for fewer
accused writers.

**The numbers:**
- `combined = (0.5 × model_score + 0.5 × style_score) / (0.5 + 0.5)`, rounded
  to 4 decimals, clamped to 0 to 1. Higher means more likely AI.
- Inside `style_signal`, two raw measures are each mapped linearly to 0 to 1
  between a human anchor (scores 0) and an AI anchor (scores 1), clamped, then
  averaged 0.5 / 0.5:
  - `sentence_length_spread`: human anchor 0.90, AI anchor 0.30
  - `punctuation_density` (commas, semicolons, dashes per word): human anchor
    0.09, AI anchor 0.04
- `type_token_ratio` has weight 0. On my samples the AI text had the higher
  value (0.979 against 0.874), the opposite of my assumption, so it is
  computed but not used.
- The anchors were chosen from six texts, so they are tuned on the data
  they were first checked against.
- Bands: human below 0.35, AI above 0.65, unsure between.

**Where it lives:** `scoring.py::combine_signals` (weights and anchors are in
`config.py`)

**A case where my two signals split, and what my rule does with it:**
`samples/clearly_human.json`: model_score 0.445, style_score 0.049, a gap of
0.396. Signal one finds it moderately predictable. Signal two finds its
sentence lengths very uneven (spread 1.128) and reads it as strongly human. The
average, 0.247, lands in the human band. The style signal's confidence carries
the text under 0.35, which signal one alone never did.

**Where the rule fails:**
`docs/formal_human.txt`, a formal paragraph written by a human. Both signals
lean AI (model 0.644, style 1.000), so there is nothing to disagree about and
averaging cannot help. Combined 0.822, higher than the clearly-AI sample
(0.813), so it would be labelled high-confidence AI. The style score hit 1.000
because its spread is ___ and its punctuation density is ___, both at or past the
AI anchors. Formal prose has long, evenly built sentences with few commas, the
same shape as the AI sample. Plain writers like Maria are not the only people
this puts at risk. I am leaving it in place and recording it, because the
trade has no free option: any change that clears this text also lets more
AI text through.


---

## Label Variants

<!-- The exact text of all three labels, as a reader would see them, and the
     score range each covers.

     Write them for someone who has never heard the word "threshold". -->

| Label | Score range | The exact text a reader sees |
|---|---|---|
| high-confidence human | 0.00 – 0.35 | We think this was most likely written by a person. |
| unsure | 0.35 – 0.65 | We can't tell for sure whether this was written by a person or by AI, so we're not making a call. |
| high-confidence AI | 0.65 – 1.00 | This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review. |

A score exactly on a boundary (0.35 or 0.65) takes the label of the more
cautious side: 0.65 counts as AI and 0.35 counts as human, matching the
comparisons in `scoring.py::score_to_label`.

**Why I worded the "unsure" one this way:**
The "unsure" label is the one most people will see, and many of them wrote
every word themselves. So it says what the system could not tell, not what the
text is. A line like "this looks like both AI and human writing" describes the
text as a mix, which a writer could read as "you used AI for part of this".
"We can't tell for sure" and "we're not making a call" put the uncertainty on
the system. It has no score, no word like "threshold", and no instruction to
the writer, because an unsure result is not an accusation and gives them
nothing to fix.

**Why I kept the AI threshold at 0.65:**
Raising it to 0.75 changes no label on my six test texts: `clearly_ai` (0.813)
stays AI and `docs/maria_{*}.txt` three poems (0.511 to 0.543) stay unsure. Six texts cannot
justify a more precise number, so I kept the original. Her margin below the AI
line is about 0.11. The cost is that a writer whose text scores just under 0.65
is not accused, while a human text that scores above it is, as `formal_human`
(0.822) shows. I will test whether this holds against the criteria in unit 8.


---

## Sample Run

<!-- One submission and one appeal, pasted as text: the request, the response,
     and the log entries. -->
**A submission**

<!-- The response needs content_id, guess, confidence, label, AND both
     signal scores - model_score and style_score. Unit 8's tools read those
     two off the response, so leaving them out costs you next unit's
     diagnostics. -->

```bash
$ curl -s -X POST http://127.0.0.1:5000/submit -H "Content-Type: application/json" -d @samples/clearly_human.json
```

```json
{
  "confidence": 0.7533,
  "content_id": "c_a27bf463c89b",
  "guess": "human",
  "label": "We think this was most likely written by a person.",
  "model_score": 0.4445,
  "style_score": 0.0489
}
```

**An appeal**

```bash
$ curl -s -X POST http://127.0.0.1:5000/appeal \
  -H "Content-Type: application/json" \
  -d "{\"content_id\": \"c_88710dd715a1\", \"reasoning\": \"I wrote this myself as part of my English class.\"}"
```

```json
{
  "content_id": "c_88710dd715a1",
  "message": "Your appeal has been recorded and this submission is under review.",
  "status": "under_review"
}
```

**What the log shows afterwards**

```bash
$ curl "http://127.0.0.1:5000/log?limit=3"
```

```json
{
  "count": 3,
  "entries": [
    {
      "combined_score": 0.2467,
      "confidence": 0.7533,
      "content_id": "c_a27bf463c89b",
      "creator_id": "demo_instructor",
      "guess": "human",
      "label": "We think this was most likely written by a person.",
      "model_score": 0.4445,
      "status": "decided",
      "style_score": 0.0489,
      "timestamp": "2026-11-01T09:22:23+00:00"
    },
    {
      "combined_score": 0.5309,
      "confidence": 0.5309,
      "content_id": "c_88710dd715a1",
      "creator_id": "maria",
      "guess": "unsure",
      "label": "We can't tell for sure whether this was written by a person or by AI, so we're not making a call.",
      "model_score": 0.5987,
      "status": "decided",
      "style_score": 0.4631,
      "timestamp": "2026-11-01T09:23:08+00:00"
    },
    {
      "content_id": "c_88710dd715a1",
      "creator_id": "maria",
      "event": "appeal",
      "reasoning": "I wrote this myself as part of my English class.",
      "status": "under_review",
      "timestamp": "2026-11-01T09:23:51+00:00"
    }
  ]
}
```

---

## How I Used AI

**Moment 1**

- *What I asked for:* Working code for the three stylometry measures, with
  help deciding how to handle text length and which direction each measure
  points.
- *What came back:* A moving-average type-token ratio, with "higher means more
  human" assumed, and a note that the punctuation direction was only a guess.
- *What I changed:* I printed the raw values on my six texts before trusting
  any of it. The AI sample had the higher type-token ratio (0.979 against
  0.874), the opposite of the assumption, so I set its weight to 0 in
  `config.py`, kept the function, and wrote "tested, not used" in the README.
  That replaced my own Milestone 1 prediction about typos and vocabulary.

**Moment 2**

- *What I asked for:* Polish for my three label drafts.
- *What came back:* My "unsure" draft said the text "looks like it is
  AI-written and human written". The feedback was that this describes the text
  as a mix, which a real writer could read as an accusation, and that my AI
  label told writers to re-check their own work instead of pointing to the
  appeal. I got rewritten versions of all three.
- *What I changed:* I used the new "unsure" wording, which says what the
  system can't tell and not what the text is. I kept the AI threshold at 0.65
  against the suggestion to raise it to 0.75, because 0.75 changed no label on
  my six texts and six texts cannot justify a more precise number. I then
  submitted one text per label to confirm all three are reachable.

<!-- ═══════════════════════ UNIT 8 — THE TEST ═══════════════════════ -->

---

## Rate Limiting

**My limits:** ___ per minute, ___ per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->

**What a caller counts as:** <!-- per address, or per creator_id? They fail
differently — one script can look like a thousand callers, and one household
can look like one. -->

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```

```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->



**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json

```

**The single worst outcome** — the one I'd least want to explain to a writer
whose work got caught by it:



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1.  |  |  |  |  |  |
| 2.  |  |  |  |  |  |
| 3.  |  |  |  |  |  |
| 4.  |  |  |  |  |  |
| 5.  |  |  |  |  |  |

**Real output from one trial**, pasted as text, naming the file and function
that produced it:

```json

```

**Diagnoses**

<!-- For each miss AND each broken attack: the stage and the mechanism.

     Your service has five stages: the route, signal one, signal two, the
     combining rule, and the label mapping.

     Not a diagnosis:  "The evasion attacks got through."
     A diagnosis:      "Four evasion inputs got through. All four had typos
                        added to AI-generated text. My second signal measures
                        word variety, and typos raise word variety — so it read
                        them as more human. My combining rule weights that
                        signal at 0.6, so it dragged the whole score down."

     Look for a pattern. Five failures on one signal is one problem, not five. -->



---

## The Improvement

**What I changed:**

**Which diagnosis pointed at it:**

### Attack Run — After

<!-- Same format. `run_attacks.py --label after` -->



**Did it help, and how do I know:**

<!-- Widening the unsure band usually fixes one problem and creates another.
     Reporting that trade honestly is worth full credit. -->



---

## What's Still Broken

<!-- For each attack still getting through and each criterion still missed:
     what you'd do, and why you stopped. -->



**The trade I'd make if this ran for real:**

<!-- Two sentences. Fewer wrong accusations means more AI text getting through.
     Say which way you'd go and WHO PAYS FOR IT. -->



<!-- ═════════════════════════════════════════════════════════════════════

     SUBMISSION CHECKLIST — unit 7

       [ ] criteria.md has five numbered criteria, each naming a target
       [ ] Each has a reason underneath
       [ ] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [ ] Two signals that measure DIFFERENT things, each with a named blind spot
       [ ] Three label variants, all reachable, written out in full
       [ ] POST /appeal changes status and writes to the log
       [ ] Signals and Scoring names scoring.py::combine_signals
       [ ] Sample Run: a submission AND an appeal, as pasted text
       [ ] At least four new commits
       [ ] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [ ] Rate limiting on /submit, with your numbers justified
       [ ] The pasted run of status codes showing 429
       [ ] Audit log with all nine fields, recording rejections too
       [ ] The attack set run IN FULL, every input with an outcome
       [ ] Ten audit log entries pasted as text
       [ ] Five criteria across three trials
       [ ] A diagnosis for every miss and every broken attack — stage AND mechanism
       [ ] One improvement, with Attack Run — After
       [ ] What's Still Broken, including the production trade
       [ ] At least four new commits
       [ ] The SAME repository URL as last unit

     Do not delete and recreate this repository.
     ═════════════════════════════════════════════════════════════════════ -->

---

📖 **How to run this project: [RUNNING.md](RUNNING.md)**
