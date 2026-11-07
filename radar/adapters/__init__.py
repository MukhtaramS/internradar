"""Pick the fetch function for a company from its config entry."""
from __future__ import annotations

from . import ats, custom

PLATFORMS = {
    "greenhouse": ats.greenhouse,
    "ashby": ats.ashby,
    "lever": ats.lever,
    "workday": ats.workday,
    "eightfold": ats.eightfold,
    "eightfold_pcsx": ats.eightfold_pcsx,
    "phenom": ats.phenom,
    "jibe": ats.jibe,
    "avature": ats.avature,
}

# adapter: custom / html entries are matched by company name.
BY_COMPANY = {
    "Google": custom.google,
    "Meta": custom.meta,
    "Apple": custom.apple,
    "Amazon": custom.amazon,
    "Jane Street": custom.jane_street,
    "Wise": custom.wise,
    "Optiver": custom.optiver,
}


def fetcher(cfg):
    """The fetch function for this company, or None if it is not scrapable yet."""
    if cfg.get("status") == "research" or cfg.get("adapter") in ("unknown", "headless"):
        return None
    return PLATFORMS.get(cfg.get("adapter")) or BY_COMPANY.get(cfg.get("name"))
