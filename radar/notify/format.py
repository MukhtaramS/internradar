"""Shared text pieces for notifications."""
from __future__ import annotations

import os
from collections import Counter

from ..config import CATEGORY_LABELS
from ..locations import country_flag, country_name

SITE_URL = os.environ.get("SITE_URL", "")
# More new jobs than this in one run (first run of a channel, a scraper coming back after
# downtime) are sent as one summary instead of one message each.
MAX_INDIVIDUAL = 15


def where(job):
    """"🇨🇭 Zurich", "🇬🇧 🇮🇪 London, Dublin", "🇩🇪 Germany" or Europe-wide."""
    if job["cities"]:
        flags = " ".join(country_flag(c) for c in job["countries"])
        return "{} {}".format(flags, ", ".join(job["cities"])).strip()
    if job["countries"]:
        return ", ".join("{} {}".format(country_flag(c), country_name(c)).strip()
                         for c in job["countries"])
    return "🇪🇺 Europe (remote or multiple)"


def details(job):
    bits = [CATEGORY_LABELS.get(job["category"], job["category"]), job["role"]]
    if job.get("degrees"):
        bits.append("/".join(job["degrees"]))
    if job.get("season"):
        bits.append(job["season"])
    return bits


def summary_lines(jobs):
    counts = Counter(j["company"] for j in jobs)
    return ["{}: {}".format(c, n) for c, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]
