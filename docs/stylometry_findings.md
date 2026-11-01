# Stylometry findings (Milestone 4)

## The lightly-edited AI text (docs/ai_edited.txt)

Source: samples/clearly_ai.json. Five edits, nothing else changed:

| Original | Edited | Targets |
|---|---|---|
| cannot be overstated | cant be overstated | typo |
| better positioned | bettr positioned | typo |
| are met | are meet | typo (wrong word) |
| strategies that can help ... productivity. First, | strategies. that can help ... productivity: first, | odd split, colon, lowercase |
| are met. Second, | are meet; second, | period to semicolon, two sentences merged |

## Scores before and after

| Text | sents | spread | punct | model | style | combined |
|---|---|---|---|---|---|---|
| clearly_ai | 8 | 0.413 | 0.043 | 0.754 | 0.871 | 0.813 |
| ai_edited | 7 | 0.486 | 0.054 | 0.505 | 0.702 | 0.603 |

Fill the blanks from the terminal output. Prediction before running it:
combined below 0.65. Result: 0.603, so the prediction held, and the text moved
from "AI" to "unsure" without a single content word changing.

## The formal human text (docs/formal_human.txt)

| model | style | combined | spread | punct |
|---|---|---|---|---|
| 0.644 | 1.000 | 0.822 | 0.193 | 0.025 |

Written by a human, scored higher than clearly_ai. Known false positive.
