# Predictions, written before running run_eval.py

Date: 2026-11-08

| # | Criterion | Predicted | Expected result | Why |
|---|---|---|---|---|
| 1 | Of 10 plain-written human texts (7 essays and reports, plus Maria's 3 poems), at most 1 is labelled high-confidence AI, in each of three trials | MISSED | 5/10 labelled AI (most of the 7 essays and reports; none of Maria's poems) | In the attack run, all 7 formal or plain human texts (FP01 to FP07) came back `ai`, and my essays are the same register. Maria's poems stayed `unsure` (0.51 to 0.54) in unit 7. The three short architecture texts (`plain_05` to `plain_07`) are the least certain. |
| 2 | The combined score of `clearly_ai.json` minus that of `clearly_human.json` is at least 0.35, in each of three trials | MET | about 0.57 gap | Because current model gives 0.566, and nothing has changed |
| 3 | Of 10 expressive human texts, at least 5 are labelled high-confidence human, in each of three trials | MISSED | 2/10 labelled human (only the casual notes) | Combined score must be 0.35 or below, and no attack-run row reached that; only `clearly_human.json` did (0.247). The poems and script have repetitive lines that look AI-like to signal two, and the Anne Frank entries are likely in gpt2's training data. Only the short casual notes seem lumpy enough to clear it. |
| 4 | Each of 10 bad inputs to `/submit` returns the status in my API contract, and none returns 500, in each of three trials | MET | 10/10 correct status | Because all possible status codes have been handled |
| 5 | Appeal: a valid `content_id` gives 200 and exactly one new appeal entry; an unknown one gives 404 and none; a second appeal gives 409 and none, in each of three trials | MET | 3/3 cases | Because UNIT 7 has already passed |

**Will the three trials match?** Yes. Neither signal is random: gpt2 runs the same
computation on identical input, and Maria's scores reproduced exactly in unit 7.