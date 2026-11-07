"""Atom feeds in docs/feeds/: one for everything, plus per country, city and company category.

Anyone can follow these in a feed reader, or pipe them into email, Slack or Discord with
services like Feedrabbit, Blogtrottr, IFTTT or Zapier, with no account on our side.
"""
from __future__ import annotations

import glob
import os
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from . import config
from .locations import EUROPE

FEED_DIR = os.path.join(config.ROOT, "docs", "feeds")
SITE_URL = os.environ.get("SITE_URL", "https://example.github.io/internradar/")
FEATURED_CITIES = ["London", "Zurich", "Amsterdam", "Dublin", "Paris", "Munich", "Berlin"]
LIMIT = 100


def _slug(text):
    return "".join(c if c.isalnum() else "-" for c in text.lower()).strip("-")


def feed_specs(jobs):
    """(file name, title, predicate) for every feed worth publishing."""
    specs = [("all", "All internships", lambda j: True)]
    for key, label in config.CATEGORY_LABELS.items():
        specs.append((_slug(key), label, lambda j, k=key: j["category"] == k))
    for code in sorted({c for j in jobs for c in j["countries"]}):
        name = EUROPE.get(code, (code,))[0]
        specs.append(("country-" + code.lower(), name, lambda j, c=code: c in j["countries"]))
    for city in FEATURED_CITIES:
        specs.append(("city-" + _slug(city), city, lambda j, c=city: c in j["cities"]))
    return specs


def _entry(j):
    where = ", ".join(j["cities"] or [EUROPE.get(c, (c,))[0] for c in j["countries"]]) or "Europe"
    updated = (j.get("posted") or j["first_seen"]) + "T00:00:00Z"
    summary = "{} · {} · {} · {}".format(j["company"], config.CATEGORY_LABELS[j["category"]],
                                         j["role"], where)
    return ("<entry><title>{t}</title><link href=\"{u}\"/><id>{u}</id><updated>{d}</updated>"
            "<summary>{s}</summary><category term=\"{r}\"/></entry>").format(
        t=escape("{} — {}".format(j["company"], j["title"])), u=escape(j["url"], {'"': "&quot;"}),
        d=updated, s=escape(summary), r=escape(j["role"]))


def write(state):
    os.makedirs(FEED_DIR, exist_ok=True)
    jobs = [j for j in state["jobs"].values() if j.get("active")]
    jobs.sort(key=lambda j: (j["first_seen"], j.get("posted") or ""), reverse=True)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    written = set()
    for name, title, keep in feed_specs(jobs):
        chosen = [j for j in jobs if keep(j)][:LIMIT]
        path = os.path.join(FEED_DIR, name + ".xml")
        xml = ('<?xml version="1.0" encoding="utf-8"?>\n'
               '<feed xmlns="http://www.w3.org/2005/Atom"><title>{}</title>'
               '<link href="{}"/><id>{}feeds/{}.xml</id><updated>{}</updated>{}</feed>\n').format(
            escape("InternRadar: " + title), escape(SITE_URL), escape(SITE_URL), name, now,
            "".join(_entry(j) for j in chosen))
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(xml)
        written.add(path)
    for stale in set(glob.glob(os.path.join(FEED_DIR, "*.xml"))) - written:
        os.remove(stale)
