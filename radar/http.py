"""HTTP helpers: one shared session, timeouts, and retries on transient errors."""
from __future__ import annotations

import time

import requests

USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
TIMEOUT = 30
RETRIES = 3
RETRY_STATUSES = {429, 500, 502, 503, 504}

session = requests.Session()
# en-US, not en-GB: some sites (SIG's Jibe board) return nothing for other English variants.
session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})


def request(method, url, *, expect="json", headers=None, **kwargs):
    """Send a request and return parsed JSON (expect="json") or text (expect="text")."""
    h = {"Accept": "application/json" if expect == "json" else "text/html,*/*"}
    h.update(headers or {})
    last = None
    for attempt in range(RETRIES):
        try:
            resp = session.request(method, url, headers=h, timeout=TIMEOUT, **kwargs)
            if resp.status_code in RETRY_STATUSES:
                raise requests.HTTPError("HTTP {}".format(resp.status_code), response=resp)
            resp.raise_for_status()
            return resp.json() if expect == "json" else resp.text
        except (requests.RequestException, ValueError) as err:
            last = err
            if attempt < RETRIES - 1:
                time.sleep(4 * (attempt + 1))
    raise RuntimeError("{} {} failed after {} tries: {}".format(method, url, RETRIES, last))


def get_json(url, **kwargs):
    return request("GET", url, **kwargs)


def post_json(url, body, **kwargs):
    headers = {"Content-Type": "application/json"}
    headers.update(kwargs.pop("headers", {}) or {})
    return request("POST", url, json=body, headers=headers, **kwargs)


def get_text(url, **kwargs):
    return request("GET", url, expect="text", **kwargs)
