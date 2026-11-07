"""Scrape every company, keep tech/quant internships in Europe, update the data, notify.

    python -m radar.main                    # full run
    python -m radar.main Google Optiver     # only these companies (for debugging)
    python -m radar.main --no-notify        # update data and site, send nothing

A company that fails is recorded in data/health.json and its listings are kept as they were;
the run only fails if every company fails.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback

from . import classify, config, feeds, site, store
from .adapters import fetcher
from .locations import parse_locations
from .notify import notify

HEALTH_PATH = os.path.join(config.ROOT, "data", "health.json")


def to_record(job, cfg):
    """Classify one scraped job. Returns a dict, or None if it is out of scope."""
    if job.is_intern is False or not job.url:
        return None
    kind = classify.kind(job.title) or ("Internship" if job.is_intern else None)
    role = classify.role(job.title)
    if not kind or not role:
        return None
    places = parse_locations(job.locations)
    europe = [p for p in places if p.in_europe]
    if not europe:
        return None
    countries = sorted({p.country for p in europe if p.country})
    return {
        "uid": job.uid,
        "company": cfg["name"],
        "category": cfg["category"],
        "title": job.title.strip(),
        "url": job.url,
        "locations": sorted({l.strip() for l in job.locations if l and l.strip()}),
        "countries": countries,
        "cities": sorted({p.city for p in europe if p.city}),
        "europe_wide": any(p.europe_wide for p in europe),
        "remote": any(p.remote for p in europe),
        "role": role,
        "kind": kind,
        "degrees": classify.degrees(job.title),
        "season": classify.season(job.title),
        "posted": job.posted,
    }


def combine(records):
    """Some sites list one job once per office (same id). Merge those into one record
    that keeps every location."""
    merged = {}
    for r in records:
        prev = merged.get(r["uid"])
        if prev is None:
            merged[r["uid"]] = r
            continue
        for key in ("locations", "countries", "cities"):
            prev[key] = sorted(set(prev[key]) | set(r[key]))
        prev["europe_wide"] = prev["europe_wide"] or r["europe_wide"]
        prev["remote"] = prev["remote"] or r["remote"]
        prev["posted"] = min(filter(None, [prev["posted"], r["posted"]]), default=None)
    return list(merged.values())


def run(only=None, send=True):
    records, succeeded, health = [], set(), {}
    for cfg in config.companies():
        name = cfg["name"]
        if only and name not in only:
            continue
        if cfg.get("enabled", True) is False:
            continue
        fetch = fetcher(cfg)
        if fetch is None:
            health[name] = {"status": "not_covered", "reason": cfg.get("notes", "")}
            continue
        started = time.time()
        try:
            jobs = fetch(cfg)
            kept = combine([r for r in (to_record(j, cfg) for j in jobs) if r])
            records.extend(kept)
            succeeded.add(name)
            health[name] = {"status": "ok", "fetched": len(jobs), "kept": len(kept),
                            "seconds": round(time.time() - started, 1)}
            print("[ok]   {:<30} {:>5} fetched {:>4} kept".format(name, len(jobs), len(kept)))
        except Exception as err:  # noqa: BLE001 - one broken company must not stop the run
            health[name] = {"status": "failed", "error": str(err)[:300]}
            print("[FAIL] {:<30} {}".format(name, err))
            traceback.print_exc()
        time.sleep(0.5)

    if not succeeded:
        print("Every company failed; leaving the data untouched.")
        return 1

    state = store.load()
    first_run = not state.get("jobs")
    added, closed, reopened = store.merge(state, records, succeeded)
    store.save(state)

    if only:
        # Partial run: keep the earlier health entries for companies not scraped now.
        old = json.load(open(HEALTH_PATH)) if os.path.exists(HEALTH_PATH) else {}
        old.update(health)
        health = old
    with open(HEALTH_PATH, "w", encoding="utf-8") as fh:
        json.dump(health, fh, indent=1, sort_keys=True)
        fh.write("\n")

    site.write(state, health)
    feeds.write(state)

    print("\nnew={} closed={} reopened={} failed={}".format(
        len(added), len(closed), len(reopened),
        sum(1 for h in health.values() if h["status"] == "failed")))
    for j in added[:50]:
        print("  + {} | {} | {}".format(j["company"], j["title"], ", ".join(j["countries"])))

    if send and not first_run:
        notify(added)
    elif first_run and added:
        print("First run: {} listings stored without notifications.".format(len(added)))

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as fh:
            fh.write("added={}\nclosed={}\nfailed={}\n".format(
                len(added), len(closed),
                sum(1 for h in health.values() if h["status"] == "failed")))
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("companies", nargs="*")
    parser.add_argument("--no-notify", action="store_true")
    args = parser.parse_args()
    sys.exit(run(only=set(args.companies) or None, send=not args.no_notify))
