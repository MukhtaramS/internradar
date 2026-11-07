"""One-off adapters for companies that run their own careers sites."""
from __future__ import annotations

import json
import re
import time

from .. import classify
from ..http import get_json, get_text, post_json, session
from ..models import Job, to_date


# ---------------------------------------------------------------------- Google --
_GOOGLE_DATA = re.compile(r"AF_initDataCallback\(\{key: 'ds:1'.*?data:(\[.*?\]), sideChannel", re.S)


def google(cfg):
    """The results page embeds its data as JSON; employment_type=INTERN filters server-side."""
    jobs = []
    for page in range(1, 25):
        html = get_text(cfg["url"], params={"q": "intern", "employment_type": "INTERN", "page": page})
        m = _GOOGLE_DATA.search(html)
        if not m:
            if page == 1:
                raise RuntimeError("Google careers page no longer has the ds:1 data block")
            break
        data = json.loads(m.group(1))
        rows = data[0] or []
        for r in rows:
            locations = [loc[0] for loc in (r[9] or []) if loc and loc[0]]
            stamp = r[12][0] if len(r) > 12 and isinstance(r[12], list) and r[12] else None
            jobs.append(Job(cfg["name"], str(r[0]), r[1] or "",
                            "{}/{}".format(cfg["url"], r[0]), locations, is_intern=True,
                            posted=to_date(stamp)))
        total = data[2] if len(data) > 2 and isinstance(data[2], int) else 0
        if not rows or len(jobs) >= total:
            break
        time.sleep(0.7)
    return jobs


# ------------------------------------------------------------------------ Meta --
_LSD = re.compile(r'"LSD",\[\],\{"token":"([^"]+)"')


def meta(cfg):
    """Meta's careers GraphQL needs a token from the HTML page and Sec-Fetch headers.
    The doc_id is a persisted-query id that changes when Meta redeploys the site."""
    nav = {"Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "none",
           "Sec-Fetch-User": "?1", "Upgrade-Insecure-Requests": "1"}
    page = session.get("https://www.metacareers.com/jobsearch/", headers=nav, timeout=30)
    page.raise_for_status()
    m = _LSD.search(page.text)
    if not m:
        raise RuntimeError("no LSD token on metacareers.com")
    resp = session.post(cfg["url"], timeout=30, headers={
        "Content-Type": "application/x-www-form-urlencoded", "x-fb-lsd": m.group(1),
        "Origin": "https://www.metacareers.com", "Referer": "https://www.metacareers.com/jobsearch/",
        "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "same-origin",
    }, data={
        "lsd": m.group(1), "fb_api_caller_class": "RelayModern",
        "fb_api_req_friendly_name": "CareersJobSearchResultsDataQuery",
        "doc_id": cfg["params"]["doc_id"],
        "variables": json.dumps({"search_input": {"q": cfg["params"].get("query", "intern")}}),
    })
    resp.raise_for_status()
    found = ((resp.json().get("data") or {}).get("job_search_with_featured_jobs") or {}).get("all_jobs")
    if found is None:
        raise RuntimeError("Meta GraphQL answered without jobs; the doc_id has probably changed")
    return [Job(cfg["name"], str(j["id"]), j.get("title", ""),
                "https://www.metacareers.com/jobs/{}".format(j["id"]), j.get("locations") or [])
            for j in found]


# ----------------------------------------------------------------------- Apple --
def apple(cfg):
    """The 'format' field is required; without it the API returns no results."""
    jobs, total = [], None
    for page in range(1, 31):
        res = post_json(cfg["url"], {
            "query": cfg["params"].get("query", "internship"), "filters": {}, "page": page,
            "locale": "en-us", "sort": "",
            "format": {"longDate": "MMMM D, YYYY", "mediumDate": "MMM D, YYYY"},
        }).get("res") or {}
        rows = res.get("searchResults") or []
        total = res.get("totalRecords", 0) if total is None else total
        if page == 1 and not rows:
            raise RuntimeError("Apple search returned nothing; check the request format")
        for j in rows:
            locations = ["{}, {}".format(l.get("name", ""), l.get("countryName", ""))
                         for l in j.get("locations") or []]
            jobs.append(Job(cfg["name"], str(j.get("positionId")), j.get("postingTitle", ""),
                            "https://jobs.apple.com/en-us/details/{}/{}".format(
                                j.get("positionId"), j.get("transformedPostingTitle", "")),
                            locations, posted=to_date(j.get("postDateInGMT"))))
        if not rows or len(jobs) >= total:
            break
        time.sleep(0.5)
    return jobs


# ---------------------------------------------------------------------- Amazon --
def amazon(cfg):
    """Two searches (text "intern" and the student-programs category), deduped."""
    jobs, seen = [], set()
    for extra in cfg["params"]["passes"]:
        offset = 0
        for _ in range(10):
            data = get_json(cfg["url"], params=dict(extra, result_limit=100, offset=offset))
            rows = data.get("jobs") or []
            for j in rows:
                jid = str(j.get("id_icims") or j.get("id"))
                if jid in seen:
                    continue
                seen.add(jid)
                where = "{}, {}".format(j.get("city", ""), j.get("country_code", "")).strip(", ")
                jobs.append(Job(cfg["name"], jid, j.get("title", ""),
                                "https://www.amazon.jobs" + j.get("job_path", ""),
                                [where or j.get("normalized_location", "")],
                                posted=to_date(j.get("posted_date"))))
            offset += 100
            if not rows or offset >= data.get("hits", 0):
                break
            time.sleep(0.5)
    return jobs


# ----------------------------------------------------------------- Jane Street --
_JS_CITIES = {"LDN": "London, United Kingdom", "AMS": "Amsterdam, Netherlands",
              "NYC": "New York, United States", "HKG": "Hong Kong", "SGP": "Singapore"}


def jane_street(cfg):
    """Internships are marked in 'availability' ("Summer Internship"), not in the title."""
    jobs = []
    for j in get_json(cfg["url"]):
        availability = j.get("availability") or ""
        is_intern = bool(re.search(r"intern|co-?op", availability, re.I))
        title = j.get("position", "")
        if is_intern:
            title = "{} ({})".format(title, availability)
        city = j.get("city") or ""
        jobs.append(Job(cfg["name"], str(j["id"]), title,
                        "https://www.janestreet.com/join-jane-street/position/{}/".format(j["id"]),
                        [_JS_CITIES.get(city, city)], is_intern=is_intern))
    return jobs


# ------------------------------------------------------------------------ Wise --
_SITEMAP_LOC = re.compile(r"<loc>\s*([^<]+?)\s*</loc>")
_JID = re.compile(r"-jid-(\d+)/?$")
_LD_JSON = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def wise(cfg):
    """The sitemap lists every job; slugs mirror titles, so only intern-like pages are opened."""
    jobs = []
    for url in _SITEMAP_LOC.findall(get_text(cfg["url"])):
        m = _JID.search(url)
        slug = url.rstrip("/").rsplit("/", 1)[-1].replace("-", " ")
        if not m or not classify.kind(slug):
            continue
        for block in _LD_JSON.findall(get_text(url)):
            try:
                posting = json.loads(block)
            except ValueError:
                continue
            if not isinstance(posting, dict) or posting.get("@type") != "JobPosting":
                continue
            places = posting.get("jobLocation") or []
            places = [places] if isinstance(places, dict) else places
            locations = [", ".join(x for x in (((p or {}).get("address") or {}).get(k)
                                               for k in ("addressLocality", "addressCountry")) if x)
                         for p in places]
            jobs.append(Job(cfg["name"], m.group(1), posting.get("title", ""), url, locations,
                            posted=to_date(posting.get("datePosted"))))
            break
        time.sleep(0.3)
    return jobs


# --------------------------------------------------------------------- Optiver --
def optiver(cfg):
    """The jobs page's own "Load more" API: GET /en/api/v1/jobs?from=N&size=M.
    Items carry title, office city and a relative href; there is no posted date."""
    jobs, start, size = [], 0, 50
    while True:
        data = get_json(cfg["url"], params={"from": start, "size": size})
        items = data.get("items") or []
        for it in items:
            href = it.get("href") or ""
            jobs.append(Job(cfg["name"], href.rstrip("/").rsplit("/", 1)[-1], it.get("title", ""),
                            "https://www.optiver.com" + href, [it.get("location", "")]))
        start += len(items)
        if not items or start >= data.get("totalCount", 0) or start > 2000:
            break
        time.sleep(0.5)
    if not jobs:
        raise RuntimeError("Optiver's jobs API returned nothing")
    return jobs
