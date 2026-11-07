"""One email per run listing the new internships, sent over SMTP.

Needs SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD and EMAIL_FROM.
Works with Gmail (app password), Brevo, Mailgun, Resend SMTP, Postmark and similar.
The channel's "to" may hold several addresses separated by commas; they are sent as Bcc.
"""
from __future__ import annotations

import html
import os
import smtplib
from email.message import EmailMessage

from . import format as fmt


def build(jobs, sender, recipients):
    msg = EmailMessage()
    msg["Subject"] = "{} new internship{} on InternRadar".format(len(jobs), "" if len(jobs) == 1 else "s")
    msg["From"] = sender
    msg["To"] = sender
    msg["Bcc"] = ", ".join(recipients)

    ordered = sorted(jobs, key=lambda j: (j["company"], j["title"]))
    text = ["{} — {}\n  {} | {}\n  {}\n".format(j["company"], j["title"], " · ".join(fmt.details(j)),
                                                fmt.where(j), j["url"]) for j in ordered]
    if fmt.SITE_URL:
        text.append("All listings: " + fmt.SITE_URL)
    msg.set_content("\n".join(text))

    e = html.escape
    rows = "".join(
        "<tr><td style='padding:8px 12px;border-bottom:1px solid #e3e6eb'>"
        "<b>{c}</b><br><a href='{u}'>{t}</a><br>"
        "<span style='color:#5a6170;font-size:13px'>{d} · {w}</span></td></tr>".format(
            c=e(j["company"]), u=e(j["url"], quote=True), t=e(j["title"]),
            d=e(" · ".join(fmt.details(j))), w=e(fmt.where(j)))
        for j in ordered)
    footer = "<p><a href='{0}'>See every listing</a></p>".format(e(fmt.SITE_URL)) if fmt.SITE_URL else ""
    msg.add_alternative(
        "<div style='font-family:system-ui,sans-serif;max-width:640px'>"
        "<h2 style='font-size:18px'>{} new internship{}</h2><table style='border-collapse:collapse;"
        "width:100%'>{}</table>{}</div>".format(len(jobs), "" if len(jobs) == 1 else "s", rows, footer),
        subtype="html")
    return msg


def send(settings, jobs):
    host = os.environ.get("SMTP_HOST")
    sender = os.environ.get("EMAIL_FROM")
    recipients = [a.strip() for a in (settings.get("to") or "").split(",") if a.strip()]
    if not (host and sender and recipients):
        return 0
    msg = build(jobs, sender, recipients)
    port = int(os.environ.get("SMTP_PORT") or 587)
    smtp_cls = smtplib.SMTP_SSL if port == 465 else smtplib.SMTP
    with smtp_cls(host, port, timeout=30) as smtp:
        if port != 465:
            smtp.starttls()
        if os.environ.get("SMTP_USER"):
            smtp.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
        smtp.send_message(msg)
    return 1
