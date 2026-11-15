#!/usr/bin/env bash
# Start the InternRadar applier: a Claude Code session in your job-search folder that takes
# requests from the InternRadar site (through your private repo) and your Telegram bot, and uses
# Chrome to apply.
#
#   applier/start.sh [job-search folder] [extra claude flags...]
#
# Leave this terminal open. The Mac stays awake while it runs (caffeinate). Stop with Ctrl+C.
set -euo pipefail

FOLDER="$HOME/InternRadar-applier"
if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then
  FOLDER="$1"
  shift
fi

if [ ! -f "$FOLDER/CLAUDE.md" ]; then
  echo "No CLAUDE.md in $FOLDER. Run $(dirname "$0")/setup.sh \"$FOLDER\" first."
  exit 1
fi
if [ -d "$FOLDER/.git" ]; then
  git -C "$FOLDER" pull --quiet --rebase --autostash || echo "Warning: couldn't pull your private repo; using the local copy."
fi
if [ -z "$(ls -A "$FOLDER/resume" 2>/dev/null)" ]; then
  echo "Warning: no CV yet. Upload one on the site (Profile & CV) before sending applications."
fi

cd "$FOLDER"
exec caffeinate -i claude \
  --channels plugin:telegram@claude-plugins-official \
  --chrome \
  "$@" \
  "You are my InternRadar applier. Read CLAUDE.md in this folder, start the queue watcher in the background as it says, then wait for requests from the site and my Telegram messages."
