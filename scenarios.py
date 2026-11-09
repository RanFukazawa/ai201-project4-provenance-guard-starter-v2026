"""
What my test runs. UNIT 8, MILESTONE 3

Criteria are numbered as in criteria.md:
  1. plain-written human texts, at most 1 of 10 labelled ai
  2. combined-score gap of at least 0.35 between clearly_ai and clearly_human
  3. expressive human texts, at least 5 of 10 labelled human
  4. bad input to /submit returns the contract status, never a 500
  5. appeal path: NOT here. run_eval.py only sends POST /submit, so criterion 5
     (and the two criterion-4 inputs that aren't dicts) are run by a separate script.

Design choices:
  - Every request carries its own creator_id, so the rate limiter (5/min) never
    turns a result into a 429. This means the eval never exercises the limiter.
  - The first 12 characters of each "texts" scenario name must be unique,
    because run_eval.py builds creator_ids from them.
  - Texts are stripped, as the route strips them, so a trailing newline
    can't shift a score.
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent


def _read(path):
    return Path(path).read_text(encoding="utf-8").strip()


def _load(folder, pattern):
    return [_read(p) for p in sorted((ROOT / folder).glob(pattern))]


def _sample(name):
    with open(ROOT / "samples" / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)["text"].strip()


# Criterion 1: 7 essays and reports, plus Maria's 3 poems (10 texts)
PLAIN = _load("eval_texts", "plain_*.txt") + [
    _read(ROOT / "docs" / f"{n}.txt")
    for n in ("maria_list", "maria_garden", "maria_journey")
]

# Criterion 3: 10 expressive texts
EXPRESSIVE = _load("eval_texts", "expressive_*.txt")

# Criterion 4 boundary inputs. Built exactly so the counts are certain.
NINE_WORDS = "One two three four five six seven eight nine"
TEN_WORDS = "One two three four five six seven eight nine ten"
CHARS_3000 = "word " * 599 + "words"     # exactly 3000 characters
CHARS_3001 = "word " * 599 + "wordss"    # exactly 3001 characters

assert len(PLAIN) == 10, f"criterion 1 needs 10 texts, found {len(PLAIN)}"
assert len(EXPRESSIVE) == 10, f"criterion 3 needs 10 texts, found {len(EXPRESSIVE)}"
assert len(NINE_WORDS.split()) == 9 and len(TEN_WORDS.split()) == 10
assert len(CHARS_3000) == 3000 and len(CHARS_3001) == 3001

SCENARIOS = [
    {
        "name": "plain_human",
        "criterion": 1,
        "texts": PLAIN,
    },
    {
        # AI sample first, human sample second. combined_score is not in the
        # response, so compute (model_score + style_score) / 2 from the report
        # (equal to combine_signals with 0.5/0.5 weights, up to rounding).
        "name": "score_gap_ai_vs_human",
        "criterion": 2,
        "texts": [_sample("clearly_ai"), _sample("clearly_human")],
    },
    {
        "name": "expressive_human",
        "criterion": 3,
        "texts": EXPRESSIVE,
    },
    {
        # Eight of the ten bad inputs. The other two (a bare JSON list and
        # unparseable JSON) are not dicts, so run_eval.py can't send them.
        # Each body has its own creator_id. "expected_status" lines up with
        # "bodies" by position; run_eval.py ignores it, but a tally can use it.
        "name": "bad_input",
        "criterion": 4,
        "bodies": [
            {"creator_id": "eval_bad_missing"},                          # no text
            {"text": "", "creator_id": "eval_bad_empty"},
            {"text": "   \n\t  ", "creator_id": "eval_bad_whitespace"},
            {"text": 12345, "creator_id": "eval_bad_number"},
            {"text": NINE_WORDS, "creator_id": "eval_bad_9words"},
            {"text": TEN_WORDS, "creator_id": "eval_ok_10words"},
            {"text": CHARS_3000, "creator_id": "eval_ok_3000chars"},
            {"text": CHARS_3001, "creator_id": "eval_bad_3001chars"},
        ],
        "expected_status": [400, 400, 400, 400, 400, 200, 200, 413],
    },
]


def validate() -> list[str]:
    """
    Complain about anything malformed, before a long run rather than during.

    A "bodies" scenario is deliberately exempt from the empty check — an empty
    string is the whole point of a bad-input case.
    """
    problems = []
    for i, scenario in enumerate(SCENARIOS, 1):
        if not scenario.get("name"):
            problems.append(f"scenario {i} has no name")

        texts = scenario.get("texts")
        bodies = scenario.get("bodies")

        if texts and bodies:
            problems.append(
                f"scenario {i} ('{scenario.get('name')}') has both texts and "
                f"bodies — pick one"
            )
            continue

        if bodies:
            for j, body in enumerate(bodies, 1):
                if not isinstance(body, dict):
                    problems.append(
                        f"scenario {i}, body {j} is not a dict — bodies are whole "
                        f"request bodies, like {{'text': '', 'creator_id': 'x'}}"
                    )
            continue

        if not texts:
            problems.append(f"scenario {i} has no texts and no bodies")
            continue

        for j, text in enumerate(texts, 1):
            if not str(text).strip():
                problems.append(
                    f"scenario {i}, text {j} is empty — if an empty submission is what "
                    f"you're testing, use 'bodies' instead of 'texts'"
                )
            elif str(text).startswith("REPLACE ME"):
                problems.append(
                    f"scenario {i} ('{scenario.get('name')}'), text {j} is still "
                    f"the placeholder"
                )

    # creator_ids for "texts" scenarios come from the first 12 characters of the name
    prefixes = [s["name"][:12] for s in SCENARIOS if s.get("texts")]
    if len(prefixes) != len(set(prefixes)):
        problems.append("two 'texts' scenarios share their first 12 name characters, "
                        "so their creator_ids would collide")
    return problems