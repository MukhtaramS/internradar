"""data/jobs.json: every internship ever seen, with first_seen / last_seen / closed dates.

Rules:
- Jobs are never deleted. A job missing from a successful scrape is marked closed.
- A closed job that reappears is reopened and keeps its first_seen date.
- If a company's scraper failed this run, its jobs are left exactly as they were.
- Every job gets a short code ("J42") that never changes or gets reused, so a reply like
  "submit J42" in Telegram names exactly one job.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from .config import ROOT

DATA_PATH = os.path.join(ROOT, "data", "jobs.json")


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load(path=DATA_PATH):
    if not os.path.exists(path):
        return {"updated_at": None, "jobs": {}}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(state, path=DATA_PATH):
    state["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def assign_codes(state):
    """Give every job without a code the next one, oldest first. Codes are never reused."""
    jobs = state.setdefault("jobs", {})
    used = [int(j["code"][1:]) for j in jobs.values() if str(j.get("code", ""))[1:].isdigit()]
    nxt = max([state.get("next_code", 1)] + [n + 1 for n in used])
    for uid in sorted((u for u, j in jobs.items() if not j.get("code")),
                      key=lambda u: (jobs[u].get("first_seen") or "", u)):
        jobs[uid]["code"] = "J{}".format(nxt)
        nxt += 1
    state["next_code"] = nxt


def by_code(state, code):
    code = code.strip().upper()
    return next((j for j in state.get("jobs", {}).values() if j.get("code") == code), None)


def merge(state, records, succeeded, date=None):
    """Merge this run's records (dicts with a "uid" key) into state.

    succeeded: names of companies whose scrape worked this run.
    Returns (added, closed, reopened) as lists of job dicts.
    """
    date = date or today()
    jobs = state.setdefault("jobs", {})
    seen = set()
    added, closed, reopened = [], [], []

    for rec in records:
        uid = rec["uid"]
        seen.add(uid)
        entry = jobs.get(uid)
        if entry is None:
            entry = dict(rec, first_seen=date, last_seen=date, active=True)
            jobs[uid] = entry
            added.append(entry)
            continue
        if not entry.get("active"):
            entry.pop("closed", None)
            reopened.append(entry)
        known_posted = entry.get("posted")
        entry.update(rec)
        if not entry.get("posted") and known_posted:
            entry["posted"] = known_posted  # some sources stop reporting old dates
        entry["last_seen"] = date
        entry["active"] = True

    for uid, entry in jobs.items():
        if uid in seen or not entry.get("active"):
            continue
        if entry["company"] in succeeded:
            entry["active"] = False
            entry["closed"] = date
            closed.append(entry)

    assign_codes(state)
    return added, closed, reopened
