"""
Signal two: the style signal. ← YOU BUILD THIS IN MILESTONE 4

Signal one reads the text for meaning. This one measures it *as text* — the
shape of it, without understanding a word.

Three measures are stubbed below because the brief names those three. They are
stubs, not implementations: what they compute is yours, and so is how you
combine them.

    sentence_length_spread   do sentences vary in length, or march in step?
    type_token_ratio         how much of the vocabulary repeats?
    punctuation_density      how much punctuation, and how varied?

Why these might differ between human and AI writing: generated prose tends
toward even, mid-length sentences and a narrower band of vocabulary, because
that's what "most likely next word" produces on average. Human writing is
lumpier — a three-word sentence next to a forty-word one.

⚠️ **The blind spot, which you have to name in Milestone 1.**

This signal cannot read. It has no idea what the text says. Anything that
changes the shape without changing the substance moves it — adding typos,
breaking up sentences, pasting in a quotation. That is a very cheap thing for
someone to do on purpose, and unit 8's attack set will do it to you.

Build each function on its own and call it from a terminal before you wire
anything together:

    python stylometry.py "some text to look at"
"""

import re
import statistics
import config

def sentences(text: str) -> list[str]:
    """Split into sentences. Rough and good enough — given to you."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def words(text: str) -> list[str]:
    """Split into lowercase words, punctuation stripped. Given to you."""
    return re.findall(r"[a-z0-9']+", text.lower())


# ── The three measures — YOU BUILD THESE ─────────────────────────────────────
NEUTRAL_SPREAD = 0.4
NEUTRAL_TTR = 0.75
NEUTRAL_PUNCT = 0.08

TTR_WINDOW = 25

def _split_sentences(text: str) -> list[str]:
    """
    Like sentences(), but a line break also ends a sentece.
    """
    pieces = []
    for line in text.splitlines():
        pieces.extend(sentences(line))
    return pieces

def sentence_length_spread(text: str) -> float:
    """
    Standard deviation of sentence length divided by the mean length.

    Scale: 0 or more, typically about 0.1 to 0.8. HIGHER = MORE HUMAN
    (lumpier). Low values mean sentences march in step.
    Edge cases: fewer than two sentences returns NEUTRAL_SPREAD, so a
    one-sentence text is neither accused nor cleared by this measure.

    Returns:
        A float. Decide yourself what scale it's on and which direction means
        "more human" — then write that down, because your combining rule
        depends on knowing it.
    """
    lengths = [len(words(s)) for s in _split_sentences(text)]
    lengths = [n for n in lengths if n > 0]
    if len(lengths) < 2:
        return NEUTRAL_SPREAD
    mean = statistics.mean(lengths)
    return statistics.stdev(lengths) / mean


def type_token_ratio(text: str) -> float:
    """
    Moving-average type-token ratio (MATTR): the unique-word ratio is
    computed in every window of TTR_WINDOW words and averaged, so long and
    short texts are comparable.

    Scale: 0 to 1. HIGHER = MORE VARIED VOCABULARY = MORE HUMAN.
    Edge cases: no words returns NEUTRAL_TTR. A text no longer than one
    window gets the plain ratio (a 14-word text will sit near 1).

    Returns:
        A float between 0 and 1. Higher means more varied vocabulary.

    Worth knowing before you rely on it: this measure falls as text gets
    longer, because common words repeat. Two texts of different lengths aren't
    directly comparable on it, and if your test inputs vary a lot in length,
    that alone can look like a signal.
    """
    toks = words(text)
    if not toks:
        return NEUTRAL_TTR
    if len(toks) <= TTR_WINDOW:
        return len(set(toks)) / len(toks)
    ratios = [
        len(set(toks[i:i+TTR_WINDOW])) / TTR_WINDOW 
        for i in range(len(toks) - TTR_WINDOW + 1)
    ]
    return sum(ratios) / len(ratios)

def punctuation_density(text: str) -> float:
    """
    Commas, semicolons and dashes (em dash, en dash, and "--") per word.
    Full stops and hyphens inside words are not counted.

    Scale: 0 or more, typically small. HIGHER = MORE HUMAN is a GUESS (the
    direction is unproven); check it on your samples before trusting it.
    Edge cases: no words returns NEUTRAL_PUNCT.

    Returns:
        A float. Whether you count all punctuation or only some kinds — commas,
        semicolons, dashes — is a real choice. Semicolons and em dashes are
        more interesting than full stops, because they vary more between
        writers.
    """
    toks = words(text)
    if not toks:
        return NEUTRAL_PUNCT
    marks = re.findall(r"--|[,;—–]", text)
    return len(marks) / len(toks)

# ── Combining them ───────────────────────────────────────────────────────────
def _to_ai_score(value: float, human_anchor: float, ai_anchor: float) -> float:
    """
    Map a raw measure onto 0-1, higher = more AI-like.
    human_anchor -> 0.0, ai_anchor -> 1.0, linear between, clamped outside.
    Works whichever anchor is larger.
    """
    span = human_anchor - ai_anchor
    if span == 0:
        return 0.5
    score = (human_anchor - value) / span
    return min(max(score, 0.0), 1.0)

def style_signal(text: str) -> float:
    """
    The style signal as a 0-1 score. HIGHER = MORE LIKELY AI.

    Two measures are used, each mapped to 0-1 with its anchors from config.py
    and then averaged by weight:
      - sentence_length_spread: low spread (even sentences) -> AI-like
      - punctuation_density:    low density (few commas/semicolons/dashes)
                                -> AI-like. The direction is unproven.
    type_token_ratio is computed in the terminal output but has weight 0.
    """
    parts = [
        (
            sentence_length_spread(text),
            config.STYLE_SPREAD_HUMAN_ANCHOR,
            config.STYLE_SPREAD_AI_ANCHOR,
            config.STYLE_WEIGHT_SPREAD,
        ),
        (
            punctuation_density(text),
            config.STYLE_PUNCT_HUMAN_ANCHOR,
            config.STYLE_PUNCT_AI_ANCHOR,
            config.STYLE_WEIGHT_PUNCT,
        ),
    ]
    total_weight = sum(w for _, _, _, w in parts)
    if total_weight == 0:
        return 0.5
    score = sum(
        _to_ai_score(value, human, ai) * w for value, human, ai, w in parts
    ) / total_weight
    return round(min(max(score, 0.0), 1.0), 4)


if __name__ == "__main__":
    import sys

    text = " ".join(sys.argv[1:]) or (
        "The system works well. It handles most cases correctly and provides "
        "good results. Users generally find it easy to use and understand."
    )

    print(f"{len(sentences(text))} sentences, {len(words(text))} words\n")
    print(f"sentence_length_spread   {sentence_length_spread(text)}")
    print(f"type_token_ratio         {type_token_ratio(text)}")
    print(f"punctuation_density      {punctuation_density(text)}")
    print(f"style_signal             {style_signal(text)}   (higher = more likely AI)")
    print("\nAll zeros? These are stubs — Milestone 4 is where you build them.")
