#!/usr/bin/env python3
"""
Criterion 4 (the two inputs run_eval.py can't send) and criterion 5 (appeal path).
Run three trials. Needs the server running.

    python run_criteria45.py --label before
"""
import argparse, datetime as dt, json, time
from pathlib import Path

import requests

import config

URL = f"http://{config.HOST}:{config.PORT}"
HDR = {"Content-Type": "application/json"}
TEXT = Path("docs/maria_garden.txt").read_text(encoding="utf-8").strip()


def appeal_entries():
    entries = requests.get(f"{URL}/log", timeout=30).json()["entries"]
    return [e for e in entries if e.get("event") == "appeal"]


def trial_c4():
    """The two non-dict bodies. Both should be 400. (429 = limiter caught it, not a valid result.)"""
    out = []
    r = requests.post(f"{URL}/submit", json=[1, 2, 3], timeout=30)
    out.append({"input": "bare JSON list [1,2,3]", "expected": 400, "status": r.status_code})
    r = requests.post(f"{URL}/submit", data='{"text": "unfinished', headers=HDR, timeout=30)
    out.append({"input": 'unparseable JSON {"text": "unfinished', "expected": 400, "status": r.status_code})
    for o in out:
        o["ok"] = o["status"] == o["expected"]
    return out


def trial_c5(n):
    cid_creator = f"eval_c5_t{n}_{int(time.time())}"
    sub = requests.post(f"{URL}/submit", json={"text": TEXT, "creator_id": cid_creator}, timeout=90)
    content_id = sub.json().get("content_id")
    cases = []

    # Case 1: valid appeal -> 200, under_review, exactly one new appeal entry
    before = len(appeal_entries())
    r = requests.post(f"{URL}/appeal", json={"content_id": content_id,
                      "reasoning": "I wrote this myself."}, timeout=30)
    after = appeal_entries()
    new = len(after) - before
    mine = [e for e in after if e.get("content_id") == content_id]
    cases.append({"case": "valid appeal", "status": r.status_code, "body": r.json(),
                  "new_appeal_entries": new, "entries_for_id": len(mine),
                  "ok": r.status_code == 200 and r.json().get("status") == "under_review" and new == 1})

    # Case 2: unknown id -> 404, no appeal entry
    before = len(appeal_entries())
    r = requests.post(f"{URL}/appeal", json={"content_id": "c_doesnotexist",
                      "reasoning": "test"}, timeout=30)
    new = len(appeal_entries()) - before
    cases.append({"case": "unknown content_id", "status": r.status_code, "body": r.json(),
                  "new_appeal_entries": new, "ok": r.status_code == 404 and new == 0})

    # Case 3: second appeal on the same id -> 409, no extra appeal entry
    before = len(appeal_entries())
    r = requests.post(f"{URL}/appeal", json={"content_id": content_id,
                      "reasoning": "Second try."}, timeout=30)
    new = len(appeal_entries()) - before
    cases.append({"case": "second appeal", "status": r.status_code, "body": r.json(),
                  "new_appeal_entries": new, "ok": r.status_code == 409 and new == 0})

    return {"content_id": content_id, "submit_status": sub.status_code, "cases": cases}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--wait", type=int, default=65,
                    help="seconds between trials, so the shared-IP limit (5/min) resets")
    args = ap.parse_args()

    report = {"criterion_4_raw_bodies": [], "criterion_5": []}
    for n in range(1, args.trials + 1):
        c4, c5 = trial_c4(), trial_c5(n)
        report["criterion_4_raw_bodies"].append(c4)
        report["criterion_5"].append(c5)
        print(f"trial {n}: c4 {sum(o['ok'] for o in c4)}/2   "
              f"c5 {sum(c['ok'] for c in c5['cases'])}/3   "
              f"statuses c4={[o['status'] for o in c4]} "
              f"c5={[c['status'] for c in c5['cases']]}")
        if n < args.trials:
            print(f"  waiting {args.wait}s for the rate limit window...")
            time.sleep(args.wait)

    config.RESULTS_DIR.mkdir(exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d_%H%M")
    path = config.RESULTS_DIR / f"criteria45_{stamp}{'_' + args.label if args.label else ''}.md"
    path.write_text("# Criteria 4 (raw bodies) and 5\n\n- Produced by: "
                    "`run_criteria45.py::main`\n\n```json\n"
                    + json.dumps(report, indent=2) + "\n```\n", encoding="utf-8")
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()