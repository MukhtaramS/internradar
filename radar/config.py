"""Load config/companies.yaml and config/notify.yaml."""
from __future__ import annotations

import os

import yaml

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_DIR = os.path.join(ROOT, "config")

CATEGORY_LABELS = {
    "faang": "FAANG",
    "faang_plus": "FAANG+",
    "quant": "Quant & Trading",
    "europe_tech": "Top European Tech",
}


def load_yaml(name):
    with open(os.path.join(CONFIG_DIR, name), encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def companies():
    return load_yaml("companies.yaml").get("companies", [])


def notify_config():
    path = os.path.join(CONFIG_DIR, "notify.yaml")
    return load_yaml("notify.yaml") if os.path.exists(path) else {}
