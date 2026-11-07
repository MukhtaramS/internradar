"""Send new internships to every channel in config/notify.yaml.

Each channel has a type (telegram, email, discord, slack) and an optional filter, so one
run can post everything to a main channel, Swiss jobs to a Switzerland channel, quant jobs
to a quant channel, and so on. A channel whose secret is not set is skipped silently, so
the project runs fine with no channels at all.
"""
from __future__ import annotations

import os
import re

from .. import config
from . import mailer, telegram, webhooks

SENDERS = {
    "telegram": telegram.send,
    "email": mailer.send,
    "discord": webhooks.discord,
    "slack": webhooks.slack,
}

# filter key -> job field it checks
FILTER_FIELDS = {
    "countries": "countries", "cities": "cities", "categories": "category",
    "roles": "role", "companies": "company", "degrees": "degrees", "kinds": "kind",
}
_ENV = re.compile(r"\$\{([A-Z0-9_]+)\}")


def expand(value):
    """Replace ${NAME} with the environment variable; empty if it is not set."""
    if not isinstance(value, str):
        return value
    return _ENV.sub(lambda m: os.environ.get(m.group(1), ""), value).strip()


def matches(job, flt):
    for key, wanted in (flt or {}).items():
        field = FILTER_FIELDS.get(key)
        if field is None:
            raise ValueError("unknown filter '{}' in notify.yaml".format(key))
        have = job.get(field)
        have = set(have) if isinstance(have, list) else {have}
        if not have & set(wanted):
            return False
    return True


def notify(added, channels=None):
    if not added:
        return
    channels = channels if channels is not None else config.notify_config().get("channels", [])
    for ch in channels:
        settings = {k: expand(v) for k, v in ch.items() if k not in ("filter",)}
        send = SENDERS.get(ch.get("type"))
        if send is None:
            print("[notify] unknown channel type: {}".format(ch.get("type")))
            continue
        jobs = [j for j in added if matches(j, ch.get("filter"))]
        if not jobs:
            continue
        try:
            sent = send(settings, jobs)
            if sent:
                print("[notify] {}: {} job(s)".format(ch.get("name", ch["type"]), len(jobs)))
        except Exception as err:  # noqa: BLE001 - a notification failure never fails the run
            print("[notify] {} failed: {}".format(ch.get("name", ch["type"]), err))
