# False-positive trace: Maria

Working notes for Milestone 1, Task 3. Steps 3 to 6 are filled in as
Milestones 4 and 5 get built. The finished version moves into the README as
"The false positive, traced: Maria", inside Signals and Scoring.

## 1. Who she is and what she wrote

Maria is a native Russian speaker who has studied English for 3 years. She
writes short poems in plain English, with common words and simple grammar.
Her work is her own, so any AI label she gets is a false positive.

| Poem | File | Words | Why it is in the set |
|---|---|---|---|
| List poem | `docs/maria_list.txt` | 14 | Very short; tests the one-sentence edge case |
| Garden poem | `docs/maria_garden.txt` | 54 | Learner grammar ("is behind my house", "it make me") |
| Journey poem | `docs/maria_journey.txt` | 93 | Same length as the samples; five long, even lines |

## 2. What signal one measured (real output, scored from files)

All scores use `.strip()` on the file contents, which is what the route will do.

| Text | Words | Perplexity | model_signal |
|---|---|---|---|
| samples/clearly_ai.json | 91 | 22.3 | 0.7544 |
| samples/clearly_human.json | 95 | 51.7 | 0.4445 |
| samples/borderline.json | 68 | 66.5 | 0.3489 |
| Maria, list poem | 14 | 36.2 | 0.5859 |
| Maria, garden poem | 54 | 35.0 | 0.5987 |
| Maria, journey poem | 93 | 34.6 | 0.6041 |

Measurement notes:

- Unstripped, a trailing newline shifted scores by up to 0.025, in either
  direction (list 38.6, garden 33.3, journey 33.6). The route should strip
  `text` before scoring.
- List poem with full stops added: 39.3 / 0.5544. Layout alone moved the score
  by about 0.03, which is small.
- Runs where I passed a file path, or literal backslash-n characters, to
  `detector.py` scored junk and are excluded.
- Numbers are from gpt2 with the midpoint at 45 and steepness 1.6. If I move
  the midpoint after calibration, these change and I record the move.

## 3. What this shows

- All three poems score well above the clearly-human sample (0.4445) and
  roughly midway to the clearly-AI sample (0.7544). The midpoint between the
  two samples is about 0.60, and Maria sits at 0.586 to 0.604.
- None crosses the current AI threshold (0.65) on signal one alone. All three
  land in "unsure" (0.35 to 0.65).
- The journey poem needs perplexity under about 30.6 to cross 0.65; she scored
  34.6, about 4 points short. With 0.5/0.5 weights it crosses 0.65 if the
  style score is about 0.70 or higher.
- The "borderline" sample scored more human than "clearly_human". A guess, not
  yet tested: British spellings, a semicolon and an em dash surprise gpt2.
- The scale is compressed. Even the clearly-human sample (0.4445) is above the
  current human threshold (0.35), so signal one alone never earns a "human"
  label on these samples.
- A trailing newline moves the score by up to 0.025 in an unpredictable
  direction. Whitespace edits are a cheap attack for unit 8.

## 4. The trace

1. **What she wrote and why it scores as predictable.** See sections 1 and 2.
   Repeated patterns and simple structure push perplexity down. Rare nouns
   (radishes, turnips) and learner grammar push it up. Measured result: the
   predictable effects win, but narrowly.
2. **What each signal returns.**
   - Signal one: 0.586 / 0.599 / 0.604 (measured).
   - Signal two: TODO (Milestone 4). Prediction to check: the journey poem has
     lines of 17 to 19 words, so low sentence-length spread and an AI-like
     style score. `stylometry.sentences()` splits only on . ! ?, so the title
     merges into line one (22 words), and the list poem counts as one sentence.
3. **Combined score.** TODO (Milestone 4).
4. **Label she sees.** TODO (Milestone 5). Quote the exact text.
5. **What that label says to her, and how it feels if wrong.** TODO.
6. **What she can do.** TODO (Milestone 5): /appeal, and her content's status
   afterwards.

## 5. Open design questions (answer in Milestones 4 and 5)

- How high must the AI threshold be so Maria is rarely labelled AI, and what
  does that cost in AI text that gets through?
- Should a line break count as a sentence boundary in `sentence_length_spread`?
  It changes how the garden and list poems are split.
- Should I move the model-signal midpoint? If so, record it in the README.
- Should the route strip `text` before scoring? Current answer: yes.
