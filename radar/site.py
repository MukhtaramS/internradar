"""Write docs/data/*.json, the files the website reads."""
from __future__ import annotations

import json
import os
import statistics
from datetime import date

from . import config
from .locations import EUROPE

SITE_DATA = os.path.join(config.ROOT, "docs", "data")
PUBLIC_FIELDS = ("company", "category", "title", "url", "locations", "countries", "cities",
                 "europe_wide", "remote", "role", "kind", "degrees", "season", "posted",
                 "first_seen")


def _days(a, b):
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def company_stats(jobs):
    """Per company: open now, ever seen, typical days a listing stays open, busiest month."""
    stats = {}
    for j in jobs:
        s = stats.setdefault(j["company"], {"open": 0, "ever": 0, "durations": [], "months": {}})
        s["ever"] += 1
        s["open"] += 1 if j.get("active") else 0
        if j.get("closed"):
            s["durations"].append(_days(j["first_seen"], j["closed"]))
        month = j["first_seen"][5:7]
        s["months"][month] = s["months"].get(month, 0) + 1
    out = {}
    for name, s in stats.items():
        out[name] = {
            "open": s["open"],
            "ever": s["ever"],
            "median_days_open": statistics.median(s["durations"]) if s["durations"] else None,
            "busiest_month": max(s["months"], key=s["months"].get) if s["months"] else None,
        }
    return out


def write(state, health):
    os.makedirs(SITE_DATA, exist_ok=True)
    all_jobs = list(state["jobs"].values())
    active = [{k: j.get(k) for k in PUBLIC_FIELDS} for j in all_jobs if j.get("active")]
    active.sort(key=lambda j: (j.get("posted") or j["first_seen"]), reverse=True)

    stats = company_stats(all_jobs)
    companies = []
    for cfg in config.companies():
        if cfg.get("enabled", True) is False:
            continue
        h = health.get(cfg["name"], {})
        companies.append(dict({
            "name": cfg["name"],
            "category": cfg["category"],
            "status": h.get("status", "not_covered"),
            "hubs": cfg.get("hubs", []),
        }, **stats.get(cfg["name"], {"open": 0, "ever": 0})))

    payload = {
        "updated_at": state["updated_at"],
        "categories": config.CATEGORY_LABELS,
        "countries": {code: {"name": v[0], "flag": v[1]} for code, v in EUROPE.items()},
        "companies": companies,
        "jobs": active,
    }
    with open(os.path.join(SITE_DATA, "jobs.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
