#!/usr/bin/env bash
# Start the InternRadar applier: a Claude Code session in your job-search folder that listens
# to your Telegram bot and uses Chrome to apply.
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
if [ -z "$(ls -A "$FOLDER/resume" 2>/dev/null)" ]; then
  echo "Warning: $FOLDER/resume is empty. Put your CV there before sending 'submit'."
fi

cd "$FOLDER"
exec caffeinate -i claude \
  --channels plugin:telegram@claude-plugins-official \
  --chrome \
  "$@" \
  "You are my InternRadar applier. Read CLAUDE.md in this folder, then wait for my Telegram messages and follow it."
