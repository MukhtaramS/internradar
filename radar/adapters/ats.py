"""Adapters for hosted careers platforms. One function per platform; config/companies.yaml
supplies the per-company settings (board token, host, ...)."""
from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone

from .. import classify
from ..http import get_json, get_text, post_json
from ..models import Job, to_date


def _place(*parts):
    return ", ".join(p for p in parts if p)


# ------------------------------------------------------------------ Greenhouse --
def greenhouse(cfg):
    data = get_json("https://boards-api.greenhouse.io/v1/boards/{}/jobs".format(cfg["token"]))
    jobs = []
    for j in data.get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        locations = [loc] if loc else []
        for office in j.get("offices") or []:
            if office.get("location"):
                locations.append(office["location"])
        jobs.append(Job(cfg["name"], str(j["id"]), j.get("title", ""), j.get("absolute_url", ""),
                        locations, posted=to_date(j.get("first_published") or j.get("updated_at"))))
    return jobs


# ----------------------------------------------------------------------- Ashby --
def _ashby_place(item):
    addr = ((item.get("address") or {}).get("postalAddress") or {})
    return _place(addr.get("addressLocality"), addr.get("addressCountry")) or item.get("location", "")


def ashby(cfg):
    data = get_json("https://api.ashbyhq.com/posting-api/job-board/{}".format(cfg["org"]))
    jobs = []
    for j in data.get("jobs", []):
        if not j.get("isListed", True):
            continue
        locations = [_ashby_place(j)] + [_ashby_place(s) for s in j.get("secondaryLocations") or []]
        jobs.append(Job(cfg["name"], str(j["id"]), j.get("title", ""), j.get("jobUrl", ""),
                        locations, is_intern=True if j.get("employmentType") == "Intern" else None,
                        posted=to_date(j.get("publishedAt"))))
    return jobs


# ----------------------------------------------------------------------- Lever --
def lever(cfg):
    data = get_json("https://api.lever.co/v0/postings/{}?mode=json".format(cfg["org"]))
    jobs = []
    for j in data:
        cats = j.get("categories") or {}
        places = cats.get("allLocations") or [cats.get("location", "")]
        country = j.get("country") or ""
        locations = [_place(p, country) for p in places if p]
        commitment = (cats.get("commitment") or "").lower()
        jobs.append(Job(cfg["name"], j["id"], j.get("text", ""), j.get("hostedUrl", ""), locations,
                        is_intern=True if "intern" in commitment else None,
                        posted=to_date(j.get("createdAt"))))
    return jobs


# --------------------------------------------------------------------- Workday --
_POSTED_RE = re.compile(r"Posted (Today|Yesterday|(\d+) Days? Ago)", re.I)
_MULTI_RE = re.compile(r"^\d+ Locations?$", re.I)


def _workday_date(text):
    m = _POSTED_RE.search(text or "")
    if not m:
        return None  # includes "30+ Days Ago", which has no exact date
    days = 0 if m.group(1).lower() == "today" else 1 if m.group(1).lower() == "yesterday" \
        else int(m.group(2))
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


def workday(cfg):
    host, site = cfg["host"], cfg["site"]
    tenant = cfg.get("tenant") or host.split(".")[0]
    base = "https://{}/wday/cxs/{}/{}".format(host, tenant, site)
    body = {"appliedFacets": cfg.get("facets", {}), "limit": 20, "offset": 0,
            "searchText": cfg.get("search", "intern")}
    jobs, total = [], None
    for _ in range(60):
        data = None
        for wait in (0, 8, 16, 24):
            # Workday's rate limiter answers 200 with an empty list; retry before believing it.
            time.sleep(wait)
            data = post_json(base + "/jobs", body)
            if data.get("jobPostings") or data.get("total"):
                break
        postings = data.get("jobPostings") or []
        if total is None:
            total = data.get("total", 0)  # only the first page reports the real total
            if not postings:
                raise RuntimeError("Workday returned an empty first page (likely rate limited)")
        for p in postings:
            title, path = p.get("title", ""), p.get("externalPath", "")
            locations = [p.get("locationsText", "")]
            if _MULTI_RE.match(locations[0]) and classify.kind(title):
                # "3 Locations": the list only lives on the job's own page
                info = get_json(base + path).get("jobPostingInfo") or {}
                locations = [info.get("location", "")] + list(info.get("additionalLocations") or [])
            bullets = p.get("bulletFields") or []
            jobs.append(Job(cfg["name"], str(bullets[0]) if bullets else path, title,
                            "https://{}/en-US/{}{}".format(host, site, path), locations,
                            posted=_workday_date(p.get("postedOn"))))
        body["offset"] += 20
        if not postings or body["offset"] >= total:
            break
        time.sleep(1)
    return jobs


# ------------------------------------------------------------------- Eightfold --
def eightfold(cfg):
    api = "https://{}/api/apply/v2/jobs".format(cfg["host"])
    jobs, start = [], 0
    for _ in range(30):
        data = get_json(api, params={"domain": cfg["domain"], "query": cfg.get("search", "intern"),
                                     "num": 100, "start": start, "sort_by": "relevance"})
        positions = data.get("positions") or []
        for p in positions:
            pid = str(p.get("id"))
            jobs.append(Job(cfg["name"], pid, p.get("name", ""),
                            p.get("canonicalPositionUrl") or
                            "https://{}/careers/job/{}".format(cfg["host"], pid),
                            [str(x) for x in (p.get("locations") or [p.get("location", "")])],
                            posted=to_date(p.get("t_create"))))
        start += len(positions)
        if not positions or start >= data.get("count", 0):
            break
        time.sleep(0.5)
    return jobs


def eightfold_pcsx(cfg):
    """Eightfold's newer search API (Microsoft). Ten results per page; two queries, deduped."""
    api = "https://{}/api/pcsx/search".format(cfg["host"])
    jobs, seen = [], set()
    for query in cfg.get("params", {}).get("queries", ["intern", "internship"]):
        start = 0
        for _ in range(40):
            data = (get_json(api, params={"domain": cfg["domain"], "query": query,
                                          "start": start, "num": 10}).get("data") or {})
            positions = data.get("positions") or []
            for p in positions:
                pid = str(p.get("id"))
                if pid in seen:
                    continue
                seen.add(pid)
                jobs.append(Job(cfg["name"], pid, p.get("name", ""),
                                "https://{}/careers/job/{}".format(cfg["host"], pid),
                                [str(x) for x in p.get("locations") or []],
                                posted=to_date(p.get("postedTs") or p.get("creationTs"))))
            start += 10
            if not positions or start >= data.get("count", 0):
                break
            time.sleep(0.7)
    return jobs


# ---------------------------------------------------------------------- Phenom --
def phenom(cfg):
    body = {"lang": "en", "deviceType": "desktop", "country": "global",
            "pageName": "search-results", "ddoKey": "refineSearch", "sortBy": "",
            "subsearch": "", "from": 0, "jobs": True, "counts": True,
            "all_fields": ["category", "country", "state", "city"], "size": 100,
            "clearAll": False, "jdsource": "facets", "isSliderEnable": False,
            "pageId": "page16", "siteType": "external", "keywords": cfg.get("search", "intern"),
            "global": True, "selected_fields": {}, "locationData": {}}
    body.update(cfg.get("body_overrides") or {})
    jobs = []
    for _ in range(10):
        data = post_json("https://{}/widgets".format(cfg["host"]), body).get("refineSearch") or {}
        batch = (data.get("data") or {}).get("jobs") or []
        for j in batch:
            locations = [j.get("cityStateCountry") or _place(j.get("city"), j.get("country"))]
            locations += [m for m in j.get("multi_location") or [] if isinstance(m, str)]
            jobs.append(Job(cfg["name"], str(j.get("jobId")), j.get("title", ""),
                            cfg["job_url"].format(id=j.get("jobId")), locations,
                            posted=to_date(j.get("postedDate") or j.get("dateCreated"))))
        body["from"] += len(batch)
        if not batch or body["from"] >= data.get("totalHits", 0):
            break
        time.sleep(0.5)
    return jobs


# ------------------------------------------------------------------------ Jibe --
def jibe(cfg):
    """Radancy/iCIMS "Jibe" career sites (SIG, Booking.com): GET {host}/api/jobs."""
    api = "https://{}/api/jobs".format(cfg["host"])
    jobs = []
    for page in range(1, 11):
        data = get_json(api, params={"keywords": cfg.get("search", "intern"), "page": page,
                                     "limit": 100})
        batch = data.get("jobs") or []
        for wrapper in batch:
            j = wrapper.get("data") or {}
            locations = [_place(j.get("city"), j.get("country")) or j.get("full_location", "")]
            for extra in j.get("additional_locations") or []:
                locations.append(_place(extra.get("city"), extra.get("country")))
            url = (j.get("meta_data") or {}).get("canonical_url") or \
                "https://{}/jobs/{}".format(cfg["host"], j.get("slug") or j.get("req_id"))
            jobs.append(Job(cfg["name"], str(j.get("req_id") or j.get("slug")), j.get("title", ""),
                            url, locations, posted=to_date(j.get("posted_date"))))
        if not batch or len(jobs) >= data.get("totalCount", 0):
            break
    return jobs


# --------------------------------------------------------------------- Avature --
_AVATURE_TITLE = re.compile(r'href="(https://[^"]+/careers/JobDetail/[^"/]+/(\d+))"[^>]*>\s*([^<]+?)\s*</a>')
_AVATURE_LOC = re.compile(r'class="list-item-location"[^>]*>\s*([^<]*?)\s*<')


def avature(cfg):
    """Server-rendered Avature boards (Bloomberg). 12 jobs per page, ?jobOffset=N."""
    url = "https://{}/careers/SearchJobs/{}".format(cfg["host"], cfg.get("params", {}).get("query", "intern"))
    jobs, seen, offset = [], set(), 0
    for _ in range(30):
        html = get_text(url, params={"jobOffset": offset} if offset else None)
        new = 0
        for block in html.split("<article")[1:]:
            m = _AVATURE_TITLE.search(block)
            if not m or m.group(2) in seen:
                continue
            seen.add(m.group(2))
            new += 1
            loc = _AVATURE_LOC.search(block)
            jobs.append(Job(cfg["name"], m.group(2), m.group(3), m.group(1),
                            [loc.group(1)] if loc else []))
        if not new:
            break
        offset += 12
        time.sleep(0.5)
    return jobs
