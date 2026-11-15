"""Post to a Telegram channel, group or private chat through a bot.

Needs TELEGRAM_BOT_TOKEN (from @BotFather) and, per channel, a chat id:
"@channel_username" or a numeric "-100..." id. The bot must be an admin of the channel.
A channel can name its own bot with `token:` (used for the personal chat).

`personal: true` is for your own chat with the applier bot: every job carries its code and
a reply hint ("submit J42"), and a large batch is listed job by job instead of summarised.
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


def personal_message(job):
    e = html.escape
    code = job.get("code") or "?"
    lines = [
        "<b>{}</b> · {}".format(e(code), e(job["company"])),
        "<b>{}</b>".format(e(job["title"])),
        "📍 {} · {}".format(e(fmt.where(job)), e(" · ".join(fmt.details(job)))),
    ]
    if job.get("posted"):
        lines.append("🗓 Posted {}".format(e(job["posted"])))
    lines.append('<a href="{}">Open posting</a>'.format(e(job["url"], quote=True)))
    lines.append("Reply <code>submit {0}</code> to apply, or <code>skip {0}</code>".format(e(code)))
    return "\n".join(lines)


def personal_list(jobs, limit=3500):
    """Many jobs at once: one line each with its code, split into messages under Telegram's limit."""
    e = html.escape
    head = "🆕 <b>{} new internships</b>. Reply <code>submit J..</code> for the ones you want.\n".format(len(jobs))
    texts, cur = [], head
    for j in jobs:
        line = '\n<b>{}</b> · {} · <a href="{}">{}</a> · {}'.format(
            e(j.get("code") or "?"), e(j["company"]), e(j["url"], quote=True), e(j["title"]), e(fmt.where(j)))
        if len(cur) + len(line) > limit:
            texts.append(cur)
            cur = ""
        cur += line
    texts.append(cur)
    return texts


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
    token = settings.get("token") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = settings.get("chat")
    if not (token and chat):
        return 0
    jobs = sorted(jobs, key=lambda j: (j["company"], j["title"]))
    if settings.get("personal"):
        texts = personal_list(jobs) if len(jobs) > fmt.MAX_INDIVIDUAL else [personal_message(j) for j in jobs]
    elif len(jobs) > fmt.MAX_INDIVIDUAL:
        texts = [summary(jobs)]
    else:
        texts = [message(j) for j in jobs]
    for i, text in enumerate(texts):
        if i:
            time.sleep(3)  # stay under Telegram's ~20 messages a minute per chat
        _post(token, chat, text)
    return len(texts)
