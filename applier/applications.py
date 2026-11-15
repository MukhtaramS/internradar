#!/usr/bin/env python3
"""The application queue shared by the InternRadar site and the applier on this Mac.

The job-search folder is a clone of your private repo. The site writes requests into
applications.json there ("submit J42", "review J45", approve, cancel); this script, run by the
Claude Code session, waits for them and reports progress back.

    python3 .applier/applications.py watch [--interval 60]
        Pull every --interval seconds and exit, printing the requests, as soon as one needs
        work (status queued, approved or cancel). Uses no Claude tokens while it waits.
    python3 .applier/applications.py set J42 working [--note "..."] [--confirmation "..."]
    python3 .applier/applications.py review J42 --cv <pdf> --record <application-record.md>
        Put the tailored CV and the filled answers in reviews/J42/ and mark it ready for review.
    python3 .applier/applications.py list
    python3 .applier/applications.py save ["message"]
        Commit and push everything else in the folder (tracker, Applications/, profile.json).

Statuses. The site sets: queued, approved, cancel. This script sets: working, review,
submitting, submitted, needs_you, cancelled, skipped, failed, closed.

Only standard library; needs git with push access to the private repo.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

FOLDER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QUEUE = os.path.join(FOLDER, "applications.json")
WAKE = ("queued", "approved", "cancel")
MAC_STATUSES = ("working", "review", "submitting", "submitted", "needs_you", "cancelled",
                "skipped", "failed", "closed")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*args, check=True):
    return subprocess.run(["git", "-C", FOLDER] + list(args), check=check,
                          capture_output=True, text=True)


def load():
    try:
        with open(QUEUE, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError):
        return {}


def dump(data):
    with open(QUEUE, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=1, sort_keys=True, ensure_ascii=False)
        fh.write("\n")


def pull():
    """Bring in the site's latest requests. Local work is kept (stashed and reapplied)."""
    return git("pull", "--rebase", "--autostash", "--quiet", check=False).returncode == 0


def commit_and_push(message, change=None, tries=5):
    """Apply `change` (a function editing the queue dict) on top of the latest remote state,
    commit everything in the folder and push. Retries if the site pushed in between."""
    for attempt in range(tries):
        pull()
        if change:
            data = load()
            change(data)
            dump(data)
        git("add", "-A")
        if git("diff", "--cached", "--quiet", check=False).returncode == 0:
            return True
        git("commit", "--quiet", "-m", message)
        if git("push", "--quiet", check=False).returncode == 0:
            return True
        # The site wrote applications.json meanwhile: drop our commit, keep the files, retry.
        git("reset", "--quiet", "--mixed", "HEAD~1")
        git("checkout", "--", "applications.json", check=False)
        time.sleep(2 + attempt * 2)
    print("Could not push to the private repo after {} tries; the change is saved locally.".format(tries),
          file=sys.stderr)
    return False


def describe(code, e):
    bits = [code, e.get("status", "?"), e.get("mode", ""), e.get("company", ""), e.get("title", ""),
            e.get("url", "")]
    return " | ".join(b for b in bits if b)


def cmd_watch(args):
    while True:
        pull()
        pending = {c: e for c, e in load().items() if e.get("status") in WAKE}
        if pending:
            print("Requests from the InternRadar site ({}):".format(now()))
            for code, e in sorted(pending.items()):
                print("  " + describe(code, e))
            print("queued+submit = apply and submit; queued+review = fill, stop before Submit, then "
                  "'review'; approved = submit the reviewed application; cancel = stop it.")
            return 0
        time.sleep(args.interval)


def cmd_set(args):
    code = args.code.upper()
    if args.status not in MAC_STATUSES:
        sys.exit("status must be one of: " + ", ".join(MAC_STATUSES))

    def change(data):
        e = data.setdefault(code, {"code": code})
        e["status"] = args.status
        e["updated"] = now()
        if args.note is not None:
            e["note"] = args.note
        if args.confirmation is not None:
            e["confirmation"] = args.confirmation
        if args.status == "submitted":
            e["submitted"] = now()
    ok = commit_and_push("{} {}".format(code, args.status), change)
    print("{} -> {}{}".format(code, args.status, "" if ok else " (not pushed yet)"))


def cmd_review(args):
    code = args.code.upper()
    folder = os.path.join(FOLDER, "reviews", code)
    os.makedirs(folder, exist_ok=True)
    review = {}
    for key, path in (("cv", args.cv), ("record", args.record), ("cover", args.cover)):
        if not path:
            continue
        if not os.path.exists(path):
            sys.exit("not found: " + path)
        target = os.path.join(folder, os.path.basename(path))
        if os.path.abspath(path) != os.path.abspath(target):
            shutil.copyfile(path, target)
        review[key] = os.path.relpath(target, FOLDER)

    def change(data):
        e = data.setdefault(code, {"code": code})
        e.update(status="review", updated=now(), review=review)
        if args.note is not None:
            e["note"] = args.note
    ok = commit_and_push("{} ready for review".format(code), change)
    print("{} -> review{}".format(code, "" if ok else " (not pushed yet)"))


def cmd_list(_args):
    pull()
    data = load()
    if not data:
        print("No applications yet.")
    for code, e in sorted(data.items(), key=lambda kv: kv[1].get("updated", ""), reverse=True):
        print(describe(code, e) + ("  # " + e["note"] if e.get("note") else ""))


def cmd_save(args):
    ok = commit_and_push(args.message or "Applier update")
    print("saved" if ok else "saved locally, push failed")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("watch")
    w.add_argument("--interval", type=int, default=60)
    s = sub.add_parser("set")
    s.add_argument("code")
    s.add_argument("status")
    s.add_argument("--note")
    s.add_argument("--confirmation")
    r = sub.add_parser("review")
    r.add_argument("code")
    r.add_argument("--cv")
    r.add_argument("--record")
    r.add_argument("--cover")
    r.add_argument("--note")
    sub.add_parser("list")
    v = sub.add_parser("save")
    v.add_argument("message", nargs="?")
    args = ap.parse_args()
    return {"watch": cmd_watch, "set": cmd_set, "review": cmd_review, "list": cmd_list,
            "save": cmd_save}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main() or 0)
