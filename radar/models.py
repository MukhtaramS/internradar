"""The one record type every adapter produces."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional


@dataclass
class Job:
    company: str
    external_id: str          # the careers system's own id, stable across runs
    title: str
    url: str
    # Location strings as close to "City, Country" as the source allows.
    locations: List[str] = field(default_factory=list)
    # True/False when the source says whether it is an internship; None = decide from the title.
    is_intern: Optional[bool] = None
    posted: Optional[str] = None  # YYYY-MM-DD

    @property
    def uid(self) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", self.company.lower()).strip("-")
        return "{}:{}".format(slug, self.external_id)


def to_date(value) -> Optional[str]:
    """Turn the date formats careers sites use into YYYY-MM-DD, or None."""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        if value > 1e12:
            value /= 1000.0
        if value < 1e9:
            return None
        return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d")
    text = str(value).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}", text):
        return text[:10]
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None
