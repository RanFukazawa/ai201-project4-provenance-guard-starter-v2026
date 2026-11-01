# API contract

Working file for Milestone 1, Task 4. A client developer should be able to
build against this without asking me a question.

Conventions: all request and response bodies are JSON (UTF-8). Scores run
from 0.0 to 1.0, and higher means more likely AI-written. Scores and
`confidence` are rounded to 4 decimal places. Every error uses one shape:
`{"error": "<code>", "message": "<sentence for a human>"}`.

---

## POST /submit

### Request

| field | type | required? | meaning / allowed values |
|---|---|---|---|
| text | string | yes | The writing to be scored. Leading and trailing whitespace is stripped first, and the stripped text must meet the length rules below. Only the first ~400 tokens (about 300 words) are scored by signal one. |
| creator_id | string | no | Identifies the submitter. If missing, empty, or not a string, it is stored as `"unknown"`. It is not echoed in the response. |

Input rules (after `.strip()`):
- Minimum length: 10 words (words are counted by splitting on whitespace)
- Maximum length: 3000 characters; longer is rejected with 413
- If `creator_id` is missing: stored as `"unknown"`
- Signal one reads only the first ~400 tokens. Signal two reads the full
  accepted text. The two scores can therefore describe different amounts of
  text on long submissions.

### Response, 200

| field | type | required? | meaning / allowed values |
|---|---|---|---|
| content_id | string | yes | Unique ID for this submission: `c_` followed by 12 hex characters. Send it to `/appeal` to challenge the result. |
| guess | string | yes | Exactly one of `"human"`, `"unsure"`, `"ai"`. |
| confidence | number | yes | 0.0 to 1.0. How sure the system is in its own `guess`. Not the AI score. |
| label | string | yes | The plain-English sentence shown to the reader. Each `guess` maps to exactly one label text. |
| model_score | number | yes | 0.0 to 1.0. Signal one (how predictable the text is). Higher means more AI-like. Never null. |
| style_score | number | yes | 0.0 to 1.0. Signal two (shape of the text). Higher means more AI-like. Never null. |

`confidence` means: how sure the system is in its own guess. With combined
score `s`:
- `"human"`: `1 − s`
- `"ai"`: `s`
- `"unsure"`: the larger of `s` and `1 − s`, capped at
  `min(1 − HUMAN_THRESHOLD, AI_THRESHOLD)`. The cap keeps an "unsure" from
  ever reporting more confidence than a "human" or "ai" at its own boundary.
  With thresholds 0.35 and 0.65 that gives 0.50 to 0.65.

Fields kept out of the response on purpose: `combined_score`, `status`,
`timestamp`, `creator_id` (internal; the log holds them).

### Errors

| situation | status | body |
|---|---|---|
| text missing / not a string / empty after strip | 400 | `{"error": "bad_request", "message": "Send JSON with a non-empty \"text\" string."}` |
| text too short (under 10 words) | 400 | `{"error": "text_too_short", "message": "Please submit at least 10 words."}` |
| text too long (over 3000 characters) | 413 | `{"error": "text_too_long", "message": "Please submit 3000 characters or fewer."}` |
| body is not valid JSON, or is JSON but not an object | 400 | `{"error": "invalid_json", "message": "Send a JSON object."}` |
| model unavailable (DetectorUnavailable) | 503 | `{"error": "detector_unavailable", "message": "The scoring model is not available right now. Try again later."}` |
| detector raises ValueError despite the route's checks (backstop) | 400 | `{"error": "text_too_short", "message": "That text is too short to score."}` |

---

## POST /appeal

### Request

| field | type | required? | meaning / allowed values |
|---|---|---|---|
| content_id | string | yes | The `content_id` returned by `/submit`. |
| reasoning | string | yes | Why the writer says the result is wrong. Non-empty after strip, at most 2000 characters. |

The appeal is attributed to the `creator_id` stored with the original
decision, not to anything the caller sends.

### Response, 200

| field | type | required? | meaning / allowed values |
|---|---|---|---|
| content_id | string | yes | Echo of the appealed ID. |
| status | string | yes | Always `"under_review"`. |
| message | string | yes | Plain-English confirmation that the appeal was recorded and the content is under review. |

Possible statuses of a piece of content: `decided` (judged, no appeal) and
`under_review` (appealed). Writers see these through `/appeal`. `rejected` is a
log status for requests that never became a decision, so it never applies to a
`content_id`. The log is append-only: status is the status of the latest
entry for that `content_id`.

### Errors

| situation | status | body |
|---|---|---|
| content_id missing or not a string | 400 | `{"error": "bad_request", "message": "Send JSON with a \"content_id\" string."}` |
| content_id does not exist | 404 | `{"error": "not_found", "message": "No submission with that content_id."}` |
| reasoning missing, empty, or over 2000 characters | 400 | `{"error": "bad_request", "message": "Send a \"reasoning\" of 1 to 2000 characters."}` |
| same content appealed a second time | 409 | `{"error": "already_under_review", "message": "This submission is already under review."}` |

---

## GET /log?limit=N

| part | type | meaning |
|---|---|---|
| query: limit | integer | Optional. A positive integer: return only the most recent N entries. |
| response: count | integer | How many entries are in `entries`. |
| response: entries | array of objects | Log entries. Decision entries carry the nine fields (timestamp, content_id, creator_id, guess, model_score, style_score, combined_score, label, status). Appeal entries carry `event: "appeal"` and `reasoning`. Rejection entries carry `event: "rejected"` and `reason`. |

Order of entries: oldest first, most recent last.
If `limit` is missing, not an integer, or 0: all entries are returned.
Negative `limit`: not supported; see the read-back note below.

---

## Read-back test

Could someone else build a client from this alone? Ambiguities I found and
fixed:
- `confidence` could be read as the AI score. Defined it as confidence in the
  guess, with a formula for each guess, including "unsure".
- The "unsure" range was tied to the current thresholds. Replaced the range
  with a rule that survives asymmetric thresholds.
- Length limits mixed tokens, words and characters. Now words for the minimum,
  characters for the maximum, tokens only for what signal one reads.
- Signals can see different amounts of text on long inputs. Documented.
- Two different 400s needed to be told apart. Gave each its own error code.
- `audit.read_entries` uses `entries[-limit:]`, so a negative limit returns
  the wrong slice. TODO: validate `limit` in the route when I build it.
