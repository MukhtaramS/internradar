"""Post to a Telegram channel or group through a bot.

Needs TELEGRAM_BOT_TOKEN (from @BotFather) and, per channel, a chat id:
"@channel_username" or a numeric "-100..." id. The bot must be an admin of the channel.
"""
from __future__ import annotations

import html
import os
import re
import time

import requests

from . import format as fmt

API = "https://api.telegram.org/bot{}/sendMessage"


def _tag(text):
    t = re.sub(r"[^0-9A-Za-z]+", "_", text).strip("_")
    return "#" + t if t else ""


def message(job):
    e = html.escape
    lines = [
        "🆕 <b>{}</b>".format(e(job["title"])),
        "🏢 {} · {}".format(e(job["company"]), e(" · ".join(fmt.details(job)))),
        "📍 {}".format(e(fmt.where(job))),
    ]
    if job.get("posted"):
        lines.append("🗓 Posted {}".format(e(job["posted"])))
    lines.append('<a href="{}">Apply →</a>'.format(e(job["url"], quote=True)))
    tags = [_tag(job["company"]), _tag(job["role"])] + [_tag(c) for c in job["cities"][:3]]
    lines.append(" ".join(t for t in tags if t))
    return "\n".join(lines)


def summary(jobs):
    lines = ["🆕 <b>{} new internships</b>\n".format(len(jobs))]
    lines += ["• " + html.escape(l) for l in fmt.summary_lines(jobs)]
    if fmt.SITE_URL:
        lines.append('\n<a href="{}">See them all →</a>'.format(fmt.SITE_URL))
    return "\n".join(lines)


def _post(token, chat, text):
    for _ in range(3):
        resp = requests.post(API.format(token), timeout=30, data={
            "chat_id": chat, "text": text, "parse_mode": "HTML",
            "disable_web_page_preview": "true"})
        if resp.status_code == 429:
            time.sleep(resp.json().get("parameters", {}).get("retry_after", 5) + 1)
            continue
        if not resp.ok:
            raise RuntimeError("Telegram HTTP {}: {}".format(resp.status_code, resp.text[:200]))
        return
    raise RuntimeError("Telegram kept rate-limiting")


def send(settings, jobs):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = settings.get("chat")
    if not (token and chat):
        return 0
    if len(jobs) > fmt.MAX_INDIVIDUAL:
        texts = [summary(jobs)]
    else:
        texts = [message(j) for j in sorted(jobs, key=lambda j: (j["company"], j["title"]))]
    for i, text in enumerate(texts):
        if i:
            time.sleep(3)  # stay under Telegram's ~20 messages a minute per chat
        _post(token, chat, text)
    return len(texts)
