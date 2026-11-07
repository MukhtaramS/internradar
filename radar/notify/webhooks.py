"""Discord and Slack incoming webhooks. The channel's "webhook" is the full webhook URL."""
from __future__ import annotations

import time

import requests

from . import format as fmt


def _post(url, payload):
    resp = requests.post(url, json=payload, timeout=30)
    if resp.status_code == 429:
        time.sleep(float(resp.headers.get("Retry-After", 5)))
        resp = requests.post(url, json=payload, timeout=30)
    if resp.status_code >= 300:
        raise RuntimeError("HTTP {}: {}".format(resp.status_code, resp.text[:200]))


def discord(settings, jobs):
    url = settings.get("webhook")
    if not url:
        return 0
    if len(jobs) > fmt.MAX_INDIVIDUAL:
        text = "**{} new internships**\n{}".format(len(jobs), "\n".join(fmt.summary_lines(jobs)))
        if fmt.SITE_URL:
            text += "\n" + fmt.SITE_URL
        _post(url, {"content": text[:1900]})
        return 1
    ordered = sorted(jobs, key=lambda j: (j["company"], j["title"]))
    sent = 0
    for i in range(0, len(ordered), 10):  # Discord allows 10 embeds per message
        embeds = [{"title": "{} — {}".format(j["company"], j["title"])[:256], "url": j["url"],
                   "description": "{}\n{}".format(" · ".join(fmt.details(j)), fmt.where(j))}
                  for j in ordered[i:i + 10]]
        _post(url, {"content": "🆕 New internships", "embeds": embeds})
        sent += 1
        time.sleep(1)
    return sent


def slack(settings, jobs):
    url = settings.get("webhook")
    if not url:
        return 0
    if len(jobs) > fmt.MAX_INDIVIDUAL:
        lines = ["*{} new internships*".format(len(jobs))] + ["• " + l for l in fmt.summary_lines(jobs)]
        if fmt.SITE_URL:
            lines.append("<{}|See them all>".format(fmt.SITE_URL))
    else:
        lines = ["*🆕 New internships*"] + [
            "• <{}|{} — {}>\n    {} · {}".format(j["url"], j["company"], j["title"],
                                                " · ".join(fmt.details(j)), fmt.where(j))
            for j in sorted(jobs, key=lambda j: (j["company"], j["title"]))]
    _post(url, {"text": "\n".join(lines)})
    return 1
