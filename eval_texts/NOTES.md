# Evaluation texts: provenance notes

Texts used by `scenarios.py` for criteria 1 and 3 in `criteria.md`. One text per
file, saved as plain `.txt` so every trial scores identical input. The route
strips whitespace before scoring, and the scenarios strip it too.

## Criterion 1: plain-written human texts (10 texts)

Target: at most 1 of 10 labelled `ai`.

**What this set is.** Seven texts of academic essay and report prose, written by
me, plus Maria's three poems from `docs/`. It is not the short, simple prose of
a casual note. It is formal-register writing by a non-native English writer, so
the result speaks to that kind of writing.

| File | What it is | Author | Register |
|---|---|---|---|
| `plain_01.txt` | Essay paragraph on human agency and literature | me | academic essay |
| `plain_02.txt` | Personal reflection on collecting stuffed animals | me | academic-style reflection |
| `plain_03.txt` | Essay on gender stereotypes in children's literature | me | academic essay |
| `plain_04.txt` | Reading response on U.S. "benevolent assimilation" | me | academic response |
| `plain_05.txt` | Description of the Guaranty Building | me | architecture report |
| `plain_06.txt` | Comparison of the Pantheon and Founders Hall | me | architecture report |
| `plain_07.txt` | Description of the Pyramid of Djoser | me | architecture report |
| `docs/maria_list.txt` | Four-line list poem | invented persona (Maria) | plain poem |
| `docs/maria_garden.txt` | Garden poem with learner grammar | invented persona (Maria) | plain poem |
| `docs/maria_journey.txt` | Five-line poem about learning English | invented persona (Maria) | plain poem |

Caveats:
- `plain_03.txt` is the longest text, at about 250 words, and is far longer than
  the others. `plain_05.txt` and `plain_07.txt` are the shortest, at about 50 words.
- Maria's poems were used to set the style anchors in unit 7, so they are not
  unseen data. A plain set of seven unseen texts plus those three is slightly
  easier than an all-new set.
- The Maria poems are written in a persona. The seven essays are my own writing.

## Criterion 3: expressive human texts (10 texts)

Target: at least 5 of 10 labelled `human`.

**What this set is.** Ten texts with a personal voice, in mixed forms. Eight are
my own writing. Two are published diary entries by Anne Frank (see below).

| File | What it is | Author | Form |
|---|---|---|---|
| `expressive_01.txt` | Free-verse poem about stress and anxiety | me | poem |
| `expressive_02.txt` | Poem about crying in colours | me | poem |
| `expressive_03.txt` | Poem titled "Wind" | me | poem |
| `expressive_04.txt` | Dialogue between River and August about a chinchilla | me | script |
| `expressive_05.txt` | Birthday and classmates, from *The Diary of a Young Girl* | **Anne Frank** | published diary |
| `expressive_06.txt` | "Dearest Kitty," the carpenter scare, from *The Diary of a Young Girl* | **Anne Frank** | published diary |
| `expressive_07.txt` | Sunday errands note | me | casual note |
| `expressive_08.txt` | Stolen umbrella | me | casual note |
| `expressive_09.txt` | Advice about avoiding a course | me | casual message |
| `expressive_10.txt` | Coffee beans mix-up | me | casual note |

Caveats:
- **`expressive_05.txt` and `expressive_06.txt` are not mine.** They are
  published entries from Anne Frank's diary. A famous published book is very
  likely in gpt2's training data, so a language model may find the text easy to
  predict. That would push `model_score` toward AI and make these two a harder
  test of whether the `human` label fires. I kept them on purpose and report
  the result with this caveat.
- I removed the original line wraps from those two entries by joining the lines,
  so a hard-wrapped line does not look like a sentence ending to `stylometry.py`.
- Four of the ten are poems or lists and one is a script. Their line breaks are
  part of the writing, so I kept them. `stylometry.py` counts a newline as a
  sentence end, so these are split by line, not by full stop.
- Texts `expressive_07` to `expressive_10` are short, at about 40 to 80 words.
  Spelling and typos are as I wrote them. I did not correct "ovetwhelmed" in
  `expressive_03.txt`.

## Texts not in these sets

- `samples/clearly_ai.json` and `samples/clearly_human.json` supply the two
  texts for criterion 2.
- Criterion 4 uses constructed inputs (empty, missing, oversized, and so on),
  not human writing.
- Criterion 5 submits one fresh text per trial and then appeals it.
