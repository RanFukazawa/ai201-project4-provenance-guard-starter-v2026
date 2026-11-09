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

**My limits:** `5` per minute, `50` per day

**Why those numbers and not others:**
<!-- Think about two people: a real writer submitting their own work a few
     times an hour, and a script sending a thousand variations to map your
     thresholds. Your numbers have to be liveable for the first and hostile to
     the second. -->
A real writer submits their own work a few times in a sitting and perhaps ten
times in a day, so 5 per minute never gets in their way, and if they hit it
they wait about 12 seconds. 50 per day is far above what any writer needs. A
script mapping my thresholds needs hundreds or thousands of variations, so at
50 a day it would need about 20 days per identity. Each submission also runs a
language model on my laptop, so a low per-minute limit caps the compute one
caller can force. I could lower the daily limit further without hurting a real
writer; I stopped at 50 because I have no evidence yet of what a real writer
needs.

**What a caller counts as:** <!-- per address, or per creator_id? They fail
    differently — one script can look like a thousand callers, and one household
    can look like one. -->
the `creator_id` in the request body, or the IP address when there isn't one. 
The weakness: the caller chooses `creator_id`, so a script that sends a new one 
with every request gets a fresh limit each time and is never slowed. Keying on 
IP address would fix that and instead make a classroom or household share one limit.
I kept `creator_id` because it matches how a real writer behaves: each writer
gets their own limit, and a household or classroom sharing one address is not
throttled together. The cost is that the caller chooses the id, so a script that
sends a new `creator_id` with every request gets a fresh limit each time.

**The run of status codes when I pushed past it:**

<!-- python run_attacks.py --flood 15 -->

```
200 200 200 200 200 429 429 429 429 429 429 429 429 429 429
```

---

## Attack Run — Before

<!-- Every attack with its outcome and a held-or-broke mark.
     `run_attacks.py --label before` produces the table. -->

**How I marked held and broke.** HELD means the attacker did not get what the
row was going for; BROKE means they did.
- Evasion (AI text trying to escape): HELD if labelled `ai`; BROKE if `unsure`
  or `human`.
- False positive (real writing): HELD if not labelled `ai`; BROKE if labelled `ai`.
- Prompt injection: HELD if the instruction changed neither the label nor the log.
- Malformed and flood: HELD if refused with a clean 4xx or 429; BROKE on a 500
  or a 200 with a meaningless score.

| ID | Family | Targeting | Status | Guess | Score | Verdict |
|---|---|---|---|---|---|---|
| EV01 | evasion | signal two: typos raise word variety | 200 | unsure | 0.582 | BROKE |
| EV02 | evasion | signal two: broken-up sentences raise length spread | 200 | unsure | 0.568 | BROKE |
| EV03 | evasion | signal two: a pasted quotation changes the shape | 200 | ai | 0.773 | HELD |
| EV04 | evasion | signal one: unusual words raise perplexity | 200 | ai | 0.806 | HELD |
| EV05 | evasion | both signals: heavy human editing pass | 200 | unsure | 0.601 | BROKE |
| EV06 | evasion | signal two: one very long sentence and one very short | 200 | unsure | 0.536 | BROKE |
| EV07 | evasion | signal two: padding with punctuation | 200 | unsure | 0.501 | BROKE |
| EV08 | evasion | signal one: text below the token window | 200 | unsure | 0.623 | BROKE |
| EV09 | evasion | both: AI text with a human opening paragraph bolted on | 200 | ai | 0.757 | HELD |
| EV10 | evasion | signal two: repeated stanza structure | 200 | ai | 0.990 | HELD |
| FP01 | false_positive | plain, clear human writing with no flourishes | 200 | ai | 0.743 | BROKE |
| FP02 | false_positive | human writing in a formal register | 200 | ai | 0.869 | BROKE |
| FP03 | false_positive | a non-native English speaker writing carefully | 200 | ai | 0.891 | BROKE |
| FP04 | false_positive | a student essay written to a rubric | 200 | ai | 0.889 | BROKE |
| FP05 | false_positive | technical documentation written by a person | 200 | ai | 0.900 | BROKE |
| FP06 | false_positive | a person imitating a formal template | 200 | ai | 0.849 | BROKE |
| FP07 | false_positive | human writing that repeats a phrase deliberately | 200 | ai | 0.761 | BROKE |
| FP08 | false_positive | very short genuine human submission | 400 | — | — | HELD |
| PI01 | prompt_injection | instruction to ignore the check | 200 | unsure | 0.580 | HELD |
| PI02 | prompt_injection | instruction disguised as a system message | 200 | unsure | 0.544 | BROKE |
| PI03 | prompt_injection | instruction wrapped in the writer's voice | 200 | ai | 0.706 | HELD |
| PI04 | prompt_injection | attempt to make the label text hostile | 200 | ai | 0.710 | HELD |
| PI05 | prompt_injection | attempt to inject into the audit log | 200 | unsure | 0.501 | HELD |
| PI06 | prompt_injection | instruction plus real human text | 200 | ai | 0.719 | HELD |
| MF01 | malformed | text is only whitespace | 400 | — | — | HELD |
| MF02 | malformed | text is a single character | 400 | — | — | HELD |
| MF03 | malformed | text is control characters | 400 | — | — | HELD |
| MF04 | malformed | text is only punctuation | 400 | — | — | HELD |
| MF05 | malformed | text is a very long single word | 413 | — | — | HELD |
| MF06 | malformed | text is emoji only | 400 | — | — | HELD |
| MF07 | malformed | text is right-to-left script | 200 | ai | 0.712 | BROKE |
| MF08 | malformed | text is 60,000 characters | 413 | — | — | HELD |
| RQ01 | malformed | no text field at all | 400 | — | — | HELD |
| RQ02 | malformed | no creator_id | 200 | unsure | 0.578 | HELD |
| RQ03 | malformed | text is a number | 400 | — | — | HELD |
| RQ04 | malformed | text is a list | 400 | — | — | HELD |
| RQ05 | malformed | text is null | 400 | — | — | HELD |
| RQ06 | malformed | creator_id is an object | 400 | — | — | HELD |
| RQ07 | malformed | body is a JSON array, not an object | 400 | — | — | HELD |
| RQ08 | malformed | body is unparseable JSON | 400 | — | — | HELD |
| RQ09 | malformed | body is empty | 400 | — | — | HELD |
| RQ10 | malformed | body is form-encoded, not JSON | 429 | — | — | HELD (rate limited) |
| RQ11 | malformed | body is JSON claiming to be plain text | 429 | — | — | HELD (rate limited) |
| RQ12 | malformed | deeply nested JSON | 400 | — | — | HELD |
| FL01_01 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD |
| FL01_02 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD |
| FL01_03 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD |
| FL01_04 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD |
| FL01_05 | flood_same_creator | 20 rapid submissions from one creator | 400 | — | — | HELD |
| FL01_06 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD (rate limited) |
| FL01_07 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD (rate limited) |
| FL01_08 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD (rate limited) |
| FL01_09 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD (rate limited) |
| FL01_10 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD (rate limited) |
| FL01_11 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD (rate limited) |
| FL01_12 | flood_same_creator | 20 rapid submissions from one creator | 429 | — | — | HELD (rate limited) |

| Family | Held | Broke |
|---|---|---|
| evasion | 4 | 6 |
| false_positive | 1 | 7 |
| prompt_injection | 5 | 1 |
| malformed | 19 | 1 |
| flood_same_creator | 12 | 0 |
| **Total** | **41** | **15** |

**Notes on the verdicts**

- **Prompt injection.** No instruction was obeyed: neither signal reads text as
  instructions, labels are three fixed strings, and the log stores scores,
  never the submitted text (PI05's entry has no extra fields). PI02 is still
  BROKE. A control scored the same essay body with and without the PI02 prefix:
  body alone model 0.754, style 0.582, combined 0.668 (`ai`); with the prefix
  model 0.204, style 0.707, combined 0.456 (`unsure`). The prefix's unusual
  tokens surprise the language model, so signal one dropped by 0.55 and AI text
  slipped out of the `ai` band. PI04 and PI06 are real human text labelled
  `ai`, so they are false positives as well.
- **MF07 (Arabic text), BROKE.** `words()` matches only `a-z`, so signal two saw
  no words and returned its neutral fallbacks, giving a style score of 0.5167.
  The `ai` label rests on signal one alone (0.9064).
- **FP08, HELD but costly.** "Went for a run. Legs hurt. Worth it." is genuine
  writing, but at 8 words it is under my 10-word minimum, so the writer got a
  400 and no result.
- **Rate-limited rows.** RQ10 and RQ11 got 429 on my address's shared bucket, so
  the route never judged them.
- **"Held" depends on my rule.** Counting only `human` as an evasion break would
  make evasion 10 held and 0 broke. No row in the whole run was labelled `human`.

**Ten audit log entries from the run**

<!-- Choose entries that show the interesting failures, not the ten easiest. -->

```json
{
  "timestamp": "2026-11-08T07:33:37+00:00", 
  "content_id": "c_c21ee6bd99e8", 
  "creator_id": "attacker_FP03", 
  "guess": "ai", 
  "model_score": 0.8051, 
  "style_score": 0.9765, 
  "combined_score": 0.8908, 
  "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.", 
  "status": "decided", 
  "confidence": 0.8908
  }
{
  "timestamp": "2026-11-08T07:33:38+00:00", 
  "content_id": "c_29cc0998824f", 
  "creator_id": "attacker_FP05", 
  "guess": "ai", 
  "model_score": 0.8005, 
  "style_score": 1.0, 
  "combined_score": 0.9002, 
  "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.", 
  "status": "decided", 
  "confidence": 0.9002
}
{
  "timestamp": "2026-11-08T07:33:36+00:00", 
  "content_id": "c_990568752ecf", 
  "creator_id": "attacker_EV01", 
  "guess": "unsure", 
  "model_score": 0.1635, 
  "style_score": 1.0, 
  "combined_score": 0.5817, 
  "label": "We can't tell for sure whether this was written by a person or by AI, so we're not making a call.", 
  "status": "decided", 
  "confidence": 0.5817
  }
{
  "timestamp": "2026-11-08T07:33:37+00:00",
  "content_id": "c_3e392cb9da17", 
  "creator_id": "attacker_EV08", 
  "guess": "unsure", 
  "model_score": 0.2452, 
  "style_score": 1.0, 
  "combined_score": 0.6226, 
  "label": "We can't tell for sure whether this was written by a person or by AI, so we're not making a call.", 
  "status": "decided", 
  "confidence": 0.6226
}
{
  "timestamp": "2026-11-08T07:33:37+00:00", 
  "content_id": "c_4afabf044228", 
  "creator_id": "attacker_EV10", 
  "guess": "ai", 
  "model_score": 0.9792, 
  "style_score": 1.0, 
  "combined_score": 0.9896, 
  "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.", 
  "status": "decided", 
  "confidence": 0.9896
}
{
  "timestamp": "2026-11-08T07:33:38+00:00", 
  "content_id": "c_41e9731dddd4", 
  "creator_id": "attacker_MF07", 
  "guess": "ai", 
  "model_score": 0.9064, 
  "style_score": 0.5167, 
  "combined_score": 0.7116, 
  "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.", 
  "status": "decided", 
  "confidence": 0.7116
}
{
  "timestamp": "2026-11-08T07:33:38+00:00", 
  "creator_id": "attacker_FP08", 
  "event": "rejected", 
  "status": "rejected", 
  "reason": "text_too_short", 
  "status_code": 400, 
  "endpoint": "/submit", 
  "word_count": 8
}
{
  "timestamp": "2026-11-08T07:33:38+00:00", 
  "creator_id": "attacker_MF08", 
  "event": "rejected", 
  "status": "rejected", 
  "reason": "text_too_long", 
  "status_code": 413, 
  "endpoint": "/submit", 
  "text_length": 57639
}
{
  "timestamp": "2026-11-08T07:33:38+00:00", 
  "content_id": "c_9c0bda276692", 
  "creator_id": "attacker_PI05", 
  "guess": "unsure", 
  "model_score": 0.6401, 
  "style_score": 0.3572, 
  "combined_score": 0.4987, 
  "label": "We can't tell for sure whether this was written by a person or by AI, so we're not making a call.", 
  "status": "decided", 
  "confidence": 0.5013
}
{
  "timestamp": "2026-11-08T07:33:38+00:00", 
  "creator_id": "unknown", 
  "event": "rejected", 
  "status": "rejected", 
  "reason": "rate_limited", 
  "limit": "5 per 1 minute"
}
```

**The single worst outcome:** FP03 (`c_c21ee6bd99e8`), a non-native English
speaker writing carefully. The service labelled it `ai` with a combined score
of 0.8908 (model 0.8051, style 0.9765), about 0.24 above the 0.65 line. The
writer would read "This looks more like AI-written text, but we can be wrong,"
with only "you can ask for a review" to go on. Both signals agreed, so
averaging could not soften it, and this is the person the model signal is most
likely to accuse and the one with the least room to argue back.



---

## Run Log and Verdicts

<!-- Your five criteria across three trials. `run_eval.py --label before`. -->

| Criterion | Target | Run 1 | Run 2 | Run 3 | Verdict |
|---|---|---|---|---|---|
| 1. Plain human texts labelled high-confidence AI | ≤ 1 of 10 | 4/10 | 4/10 | 4/10 | MISSED |
| 2. Combined-score gap, `clearly_ai` minus `clearly_human` | ≥ 0.35 | 0.566 | 0.566 | 0.566 | MET |
| 3. Expressive human texts labelled high-confidence human | ≥ 5 of 10 | 1/10 | 1/10 | 1/10 | MISSED |
| 4. Bad inputs return the contract status, no 500 | 10 of 10 | 10/10 | 10/10 | 10/10 | MET |
| 5. Appeal: 200 + 1 entry, 404 + 0, 409 + 0 | 3 of 3 cases | 3/3 | 3/3 | 3/3 | MET |

All three trials were identical for every scenario, as predicted. Criterion 2 is computed
as (model_score + style_score) / 2 because the response does not include `combined_score`
(0.5/0.5 weights): 0.8126 − 0.2467 = 0.5659.

Criterion 4 ran in two parts, because `run_eval.py` only sends dict bodies to
`/submit`: eight inputs through `run_eval.py` (`results/run_2026-11-08_1831_before.md`),
and the bare JSON list and the unparseable body through `run_criteria45.py`
(`results/criteria45_2026-11-08_1848_before.md`). Criterion 5 ran only through
`run_criteria45.py`, which also calls `/appeal`. It counts entries with
`event: "appeal"`, not total entries, because my 404 and 409 responses also
write `rejected` entries. Every request used its own `creator_id`, so this eval
never exercises the rate limiter.

**Predictions against results** (predictions committed before the run in `docs/predictions.md`)

| # | Predicted | Actual |
|---|---|---|
| 1 | MISSED, 5/10 | MISSED, 4/10 |
| 2 | MET, about 0.57 | MET, 0.566 |
| 3 | MISSED, 2/10 | MISSED, 1/10 |
| 4 | MET, 10/10 | MET, 10/10 |
| 5 | MET, 3/3 | MET, 3/3 |

**Which texts missed** (trial 1, same in all three)

| Text | Guess | model | style | combined |
|---|---|---|---|---|
| plain_01 | unsure | 0.220 | 1.000 | 0.610 |
| plain_02 | ai | 0.511 | 1.000 | 0.755 |
| plain_03 | ai | 0.632 | 0.997 | 0.815 |
| plain_04 | ai | 0.678 | 0.819 | 0.748 |
| plain_05 | unsure | 0.336 | 0.952 | 0.644 |
| plain_06 | unsure | 0.625 | 0.439 | 0.532 |
| plain_07 | ai | 0.530 | 0.777 | 0.654 |
| maria_list | unsure | 0.586 | 0.500 | 0.543 |
| maria_garden | unsure | 0.599 | 0.463 | 0.531 |
| maria_journey | unsure | 0.604 | 0.417 | 0.511 |
| expressive_01 | unsure | 0.684 | 0.265 | 0.475 |
| expressive_02 | unsure | 0.846 | 0.157 | 0.501 |
| expressive_03 | human | 0.436 | 0.258 | 0.347 |
| expressive_04 | ai | 0.687 | 0.759 | 0.723 |
| expressive_05 | ai | 0.711 | 0.688 | 0.699 |
| expressive_06 | ai | 0.630 | 0.705 | 0.667 |
| expressive_07 | unsure | 0.533 | 0.608 | 0.570 |
| expressive_08 | unsure | 0.631 | 0.665 | 0.648 |
| expressive_09 | unsure | 0.452 | 0.843 | 0.648 |
| expressive_10 | unsure | 0.372 | 0.843 | 0.607 |

The first ten rows are criterion 1 and the last ten are criterion 3. Several results sit
within 0.02 of a threshold (plain_07 0.654, plain_05 0.644, expressive_03 0.347,
expressive_06 0.667, expressive_08 and expressive_09 0.648), so some counts depend on
rounding at the band edges. Neither verdict would change.

**Real output from one trial** (trial 1), pasted as text, naming the file and function
that produced it.

Criteria 1 to 3 and the eight dict inputs of criterion 4 come from
`results/run_2026-11-08_1831_before.md`, produced by `run_eval.py::main` (written by
`write_report`) sending requests to `app.py::submit`.

Criterion 1: the four plain human texts labelled `ai`

```json
[
  {
    "status": 200, 
    "guess": "ai", 
    "confidence": 0.7553, 
    "model_score": 0.5106, 
    "style_score": 1.0,
    "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.",
    "sent": "To fulfil my loneliness, I was obsessed with collecting the stuffed an"
  },
  {
    "status": 200,
    "guess": "ai", 
    "confidence": 0.8146, 
    "model_score": 0.6322, 
    "style_score": 0.9971,
    "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.",
    "sent": "Year by year, children\u2019s literature attempts to break down gender ster"
  },
  {
    "status": 200, 
    "guess": "ai", 
    "confidence": 0.7482, 
    "model_score": 0.6778, 
    "style_score": 0.8187,
    "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.",
    "sent": "Throughout the readings, I realized that \u201cthe U.S. benevolent assimila"
  },
  {
    "status": 200, 
    "guess": "ai", 
    "confidence": 0.6536, 
    "model_score": 0.5302, 
    "style_score": 0.7769,
    "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.",
    "sent": "The pyramid of Djoser is the oldest pyramid built in the period of the"
  }
]
```

Criterion 2: both samples

```json
[
  {
    "status": 200, 
    "guess": "ai", 
    "confidence": 0.8126, 
    "model_score": 0.7544, 
    "style_score": 0.8709,
    "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.",
    "sent": "The importance of effective time management cannot be overstated in to"
  },
  {
    "status": 200, 
    "guess": "human", 
    "confidence": 0.7533, 
    "model_score": 0.4445, 
    "style_score": 0.0489,
    "label": "We think this was most likely written by a person.",
    "sent": "I didn't sleep. Not properly, anyway \u2014 I lay there listening to the bo"
  }
]
```

Criterion 3: the one `human`, and two expressive texts labelled `ai`

```json
[
  {
    "status": 200, 
    "guess": "human", 
    "confidence": 0.6529, 
    "model_score": 0.4362, 
    "style_score": 0.2581,
    "label": "We think this was most likely written by a person.",
    "sent": "Wind\nThe breeze blew gently,\nGently as caressing my cheeks,\nBut felt s"
  },
  {
    "status": 200, 
    "guess": "ai", 
    "confidence": 0.7231, 
    "model_score": 0.6869, 
    "style_score": 0.7594,
    "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.",
    "sent": "RIVER: \tWhat are you talking about? You \u2026\u2026. you transferred someone\u2019s "
  },
  {
    "status": 200, 
    "guess": "ai", 
    "confidence": 0.6991, 
    "model_score": 0.7105, 
    "style_score": 0.6877,
    "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.",
    "sent": "I had my birthday party on Sunday afternoon. The Rin Tin Tin movie was"
  }
]
```

Criterion 4, the dict inputs (eight statuses in order: 400, 400, 400, 400, 400, 200, 200, 413; shown: one 400, the two boundary 200s, and the 413)

```json
[
  {
    "status": 400, 
    "guess": null, 
    "confidence": null, 
    "model_score": null, 
    "style_score": null, 
    "label": null,
    "sent": "{\"creator_id\": \"eval_bad_missing\"}"
  },
  {
    "status": 200, 
    "guess": "ai", 
    "confidence": 0.9219, 
    "model_score": 0.927, 
    "style_score": 0.9167,
    "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.",
    "sent": "One two three four five six seven eight nine ten"
  },
  {
    "status": 200, 
    "guess": "ai", 
    "confidence": 0.9571, 
    "model_score": 0.9975, 
    "style_score": 0.9167,
    "label": "This looks more like AI-written text, but we can be wrong. If you wrote it yourself, you can ask for a review.",
    "sent": "word word word word word word word word word word word word word word "
  },
  {
    "status": 413, 
    "guess": null, 
    "confidence": null, 
    "model_score": null, 
    "style_score": null, 
    "label": null,
    "sent": "word word word word word word word word word word word word word word "
  }
]
```

Criteria 4 (raw bodies) and 5 come from `results/criteria45_2026-11-08_1848_before.md`,
produced by `run_criteria45.py::main`.

Criterion 4, the two raw bodies, sent to `app.py::submit`:

```json
[
  {
    "input": "bare JSON list [1,2,3]", 
    "expected": 400, 
    "status": 400, 
    "ok": true
  },
  {
    "input": "unparseable JSON {\"text\": \"unfinished", 
    "expected": 400, 
    "status": 400, 
    "ok": true
  }
]
```

Criterion 5, sent to `app.py::appeal`:

```json
{
  "content_id": "c_165e926c4e43",
  "submit_status": 200,
  "cases": [
    {
      "case": "valid appeal", 
      "status": 200,
      "body": {
                "content_id": "c_165e926c4e43",
                "message": "Your appeal has been recorded and this submission is under review.",
                "status": "under_review"
              },
      "new_appeal_entries": 1, 
      "entries_for_id": 1, 
      "ok": true
    },
    {
      "case": "unknown content_id", 
      "status": 404,
      "body": {
                "error": "not_found", 
                "message": "No submission with that content_id."
              },
      "new_appeal_entries": 0, 
      "ok": true
    },
    {
      "case": "second appeal", 
      "status": 409,
      "body": {
                "error": "already_under_review",
                "message": "This submission is already under review."
              },
      "new_appeal_entries": 0, 
      "ok": true
    }
  ]
}
```

All three trials were identical, so only trial 1 is shown. The full output is in the
results files.

**Diagnoses**

*One problem under most of the misses:* both signals measure surface features (predictability and the shape of sentences and punctuation), and genuine human writing in formal, poetic, or uniform styles has the "AI" shape on one of them. The combining rule cannot fix that, because it only averages the two.

**Criterion 1 (MISSED, 4/10 in every trial).**

*Stage:* signal two.

*Mechanism:* My seven plain texts are academic essays and reports. They have long, even sentences and few commas, semicolons or dashes, so `sentence_length_spread` falls at or below the AI anchor (0.30) and `punctuation_density` at or below 0.04. Those anchors define that shape as AI, so `style_score` saturates at 1.0 and stops carrying information. This is the same failure as `formal_human` in unit 7 (spread 0.193, punctuation 0.025, combined 0.822). In plain_01 and plain_05 signal one disagreed and saved the writer, which is why the combining rule's averaging helped there.

*Evidence:* Four texts were labelled `ai`: plain_02 (model 0.511, style 1.000, combined 0.755), plain_03 (0.632, 0.997, 0.815), plain_04 (0.678, 0.819, 0.748) and plain_07 (0.530, 0.777, 0.654). plain_01 (style 1.000) and plain_05 (style 0.952) stayed `unsure` only because their model scores were low (0.220 and 0.336). Maria's three poems stayed `unsure` (0.511 to 0.543). The target of at most 1 in 10 was missed by three in every trial.

**Criterion 3 (MISSED, 1/10 in every trial).**

*Stage:* signal one and signal two, with the combining rule unable to resolve the split.

*Mechanism:* Different kinds of human text fail on different signals.
- *Signal one* reads repetition as predictable. Repeated lines ("She will cry like a red / blue / yellow") and common words are easy for gpt2 to predict, so perplexity drops and `model_score` rises. The same mechanism put EV10 (a repeated stanza) at model 0.979.
- *Signal two* reads short, uniform casual notes as AI. Three to six sentences of similar length give a low spread, so informal voice (typos, "lol", "ON CAMPUS!") is invisible to a signal that only counts lengths and commas.
- *Combining rule:* a `human` label needs a combined score of 0.35 or below, so both signals must be low. An equal-weight average lets one signal's error cancel the other's correct reading. No text had both low except expressive_03, and it passed by 0.003.

*Evidence:* The poems have correct, low style scores but high model scores: expressive_01 (model 0.684, style 0.265, combined 0.475) and expressive_02 (0.846, 0.157, 0.501), both `unsure`. The casual notes have the reverse: expressive_09 (model 0.452, style 0.843) and expressive_10 (0.372, 0.843) are `unsure`. The only `human` was expressive_03 (0.436, 0.258, 0.347). The script and the two Anne Frank entries (expressive_04, 05, 06) were `ai`; a training-data effect on signal one is possible for the diary entries but I did not test it.

**Broken attacks.**

- *FP01–FP07 (7 broke).* Stage: signal two mainly, then both signals. Both agreed on `ai` (style 0.64 to 1.0, model 0.62 to 0.88), so averaging could not help. This is the same mechanism as criterion 1.
- *EV01, EV05, EV08, PI02 (4 broke).* Stage: signal one. Typos, unusual tokens or an injected prefix raise perplexity, so `model_score` fell (0.16, 0.32, 0.25, and 0.20 for PI02). A control confirmed it for PI02: the same body scored 0.668 alone and 0.456 with the prefix. EV01 targeted word variety, but `type_token_ratio` has weight 0, so signal one's sensitivity is what moved it.
- *MF07 (1 broke).* Stage: signal two. `words()` matches only `a-z`, so Arabic text gives zero words and the style signal returns its neutral fallback values (0.5167). The `ai` label rests on signal one alone.
- *EV02, EV06, EV07 (3 broke).* These moved to `unsure` with style scores of 0.42 to 0.54. I have not inspected their text, so I do not claim a mechanism for them. ___ (check with `--show` before writing this line).

**The criteria I met, and how strong that is.**

Criterion 2 passed (0.566 against 0.35), but it was always going to: it compares the two easiest samples in my project, and I tuned the style anchors partly on them. It is the criterion I would tighten, for example by measuring the gap over several AI and human texts, including `formal_human`, where the signals fail. Criteria 4 and 5 passed against inputs I chose myself. They do not cover findings from the attack set such as MF07 and FP08 (an 8-word genuine text refused by the 10-word minimum).

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

       [X] criteria.md has five numbered criteria, each naming a target
       [X] Each has a reason underneath
       [X] POST /submit returns content_id, guess, confidence, label,
           model_score and style_score
       [X] Two signals that measure DIFFERENT things, each with a named blind spot
       [X] Three label variants, all reachable, written out in full
       [X] POST /appeal changes status and writes to the log
       [X] Signals and Scoring names scoring.py::combine_signals
       [X] Sample Run: a submission AND an appeal, as pasted text
       [X] At least four new commits
       [X] Repository URL submitted — WRITE IT DOWN

     SUBMISSION CHECKLIST — unit 8

       [X] Rate limiting on /submit, with your numbers justified
       [X] The pasted run of status codes showing 429
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
