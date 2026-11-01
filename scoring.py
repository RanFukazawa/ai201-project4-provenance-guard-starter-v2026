"""
Turning two numbers into one, and one number into something a person can read.
← YOU BUILD THIS IN MILESTONES 4 AND 5

Two functions live here, and both are stubs.

`combine_signals` is where your false-positive decision from Milestone 1
actually gets made. Everything above it — the labels, the appeal path — is
downstream of a number this function produced.

`score_to_label` is where you stop writing for a machine and start writing for
a person. A score of 0.62 means nothing to a writer.

⚠️ Your README's **Signals and Scoring** section has to name the file and
function holding your combining rule. The grader checks your code against what
you claim, so that line should read `scoring.py::combine_signals`.
"""

import config

LABEL_HUMAN = "We think this was most likely written by a person."
LABEL_UNSURE = (
    "We can't tell for sure whether this was written by a person or by AI, "
    "so we're not making a call."
)
LABEL_AI = (
    "This looks more like AI-written text, but we can be wrong. "
    "If you wrote it yourself, you can ask for a review."
)

def combine_signals(model_score: float, style_score: float) -> float:
    """
    Weighted average of the two signals (weights in config.py), 0-1,
    higher = more likely AI. When the signals disagree, the average lands
    between them, usually in the "unsure" band: two methods disagreeing is
    treated as uncertainty, not resolved in favour of either.

    Args:
        model_score: from `detector.model_signal` — how predictable the text is.
        style_score: from `stylometry.style_signal` — the shape of the text.

    Returns:
        A float from 0.0 (confidently human) to 1.0 (confidently AI).
    """
    total = config.WEIGHT_MODEL_SIGNAL + config.WEIGHT_STYLE_SIGNAL
    score = (
        config.WEIGHT_MODEL_SIGNAL * model_score
        + config.WEIGHT_STYLE_SIGNAL * style_score
    ) / total
    return round(min(max(score, 0.0), 1.0), 4)


def score_to_label(score: float) -> tuple[str, str]:
    """
    Turn a combined score into (guess, label_text).

    A score exactly on a threshold takes the more cautious reading:
    >= AI_THRESHOLD is "ai" and <= HUMAN_THRESHOLD is "human".

    Returns:
        (guess, label_text) — where `guess` is a short machine-readable string
        like "ai" / "human" / "unsure", and `label_text` is the full sentence
        shown to a person.
    """
    if score >= config.AI_THRESHOLD:
        return "ai", LABEL_AI
    if score <= config.HUMAN_THRESHOLD:
        return "human", LABEL_HUMAN
    return "unsure", LABEL_UNSURE


def confidence(score: float, guess: str) -> float:
    """
    How sure the system is in its own guess (not the AI score), 0-1.

      human:  1 - score
      ai:     score
      unsure: the larger of score and 1 - score, capped at
              min(1 - HUMAN_THRESHOLD, AI_THRESHOLD), so an "unsure" never
              reports more confidence than a human or ai at its own boundary.
    """
    if guess == "human":
        value = 1 - score
    elif guess == "ai":
        value = score
    else:
        cap = min(1 - config.HUMAN_THRESHOLD, config.AI_THRESHOLD)
        value = min(max(score, 1 - score), cap)
    return round(min(max(value, 0.0), 1.0), 4)


def label_ranges() -> list[tuple[str, str]]:
    """
    The score range each label covers. Your README needs these beside the
    label text — given to you so the numbers can't drift apart from config.py.
    """
    return [
        ("high-confidence human", f"0.00 – {config.HUMAN_THRESHOLD:.2f}"),
        ("unsure", f"{config.HUMAN_THRESHOLD:.2f} – {config.AI_THRESHOLD:.2f}"),
        ("high-confidence AI", f"{config.AI_THRESHOLD:.2f} – 1.00"),
    ]
