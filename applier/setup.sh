#!/usr/bin/env bash
# One-time setup for the InternRadar applier on a Mac.
#
#   applier/setup.sh [job-search folder] [owner/private-repo]
#       folder default: ~/InternRadar-applier
#       repo default:   <your GitHub user>/internradar-private (created private if missing)
#
# It installs the AutoInternship skills for Claude Code, the Python packages they use, and makes
# the job-search folder with this applier's instructions. The folder is a clone of a private
# GitHub repo, which the InternRadar site uses for your profile, CV and application requests.
# It never overwrites your files.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
FOLDER="${1:-$HOME/InternRadar-applier}"
REPO="${2:-}"
SKILLS="$HOME/.claude/skills"
SRC="$HOME/.claude/autointernship-src"
missing=0

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "  ✗ $1 is not installed. $2"
    missing=1
  else
    echo "  ✓ $1"
  fi
}

say "Checking tools"
need claude "Install Claude Code: https://code.claude.com/docs/en/quickstart"
need bun "The Telegram channel needs it. Install: curl -fsSL https://bun.sh/install | bash"
need git "Install the Xcode command line tools: xcode-select --install"
need python3 "Install Python 3: https://www.python.org/downloads/"
need gh "The GitHub CLI, for the private repo: brew install gh, then gh auth login"
if [ "$missing" = 1 ]; then
  echo
  echo "Install what's missing above, then run this again."
  exit 1
fi

say "Installing the AutoInternship skills into $SKILLS"
if [ -d "$SRC/.git" ]; then
  git -C "$SRC" pull --quiet --ff-only
else
  git clone --quiet --depth 1 https://github.com/pqthangv/AutoInternshipClaude.git "$SRC"
fi
mkdir -p "$SKILLS"
for skill in internship-application internship-tracker; do
  rm -rf "$SKILLS/$skill.tmp"
  cp -R "$SRC/$skill" "$SKILLS/$skill.tmp"
  rm -rf "$SKILLS/$skill"
  mv "$SKILLS/$skill.tmp" "$SKILLS/$skill"
  echo "  ✓ $skill"
done

say "Installing Python packages the skills use (openpyxl, pypdf)"
if python3 -c "import openpyxl, pypdf" 2>/dev/null; then
  echo "  ✓ already installed"
else
  if python3 -m pip install --user --quiet --disable-pip-version-check openpyxl pypdf; then
    echo "  ✓ installed"
  else
    echo "  ✗ pip failed. Run: python3 -m pip install --user openpyxl pypdf"
  fi
fi
command -v tectonic >/dev/null 2>&1 && echo "  ✓ tectonic (builds Overleaf CVs)" ||
  echo "  · tectonic not found: only needed if your CV is an Overleaf (LaTeX) project. See https://tectonic-typesetting.github.io/"

say "Setting up your job-search folder: $FOLDER"
mkdir -p "$FOLDER/resume"
if [ -f "$FOLDER/CLAUDE.md" ] && ! cmp -s "$HERE/CLAUDE.md" "$FOLDER/CLAUDE.md"; then
  cp "$HERE/CLAUDE.md" "$FOLDER/CLAUDE.md.new"
  echo "  · CLAUDE.md already exists and differs; the latest version is in CLAUDE.md.new"
else
  cp "$HERE/CLAUDE.md" "$FOLDER/CLAUDE.md"
  echo "  ✓ CLAUDE.md (the applier's instructions)"
fi
[ -f "$FOLDER/jobs.txt" ] || printf '# Links waiting to be applied to, one per line.\n\n# done\n' > "$FOLDER/jobs.txt"
[ -f "$FOLDER/applications.json" ] || printf '{}\n' > "$FOLDER/applications.json"
[ -f "$FOLDER/.gitignore" ] || printf '.DS_Store\n*.tmp\n~$*\n' > "$FOLDER/.gitignore"
mkdir -p "$FOLDER/.applier"
cp "$HERE/applications.py" "$FOLDER/.applier/applications.py"
echo "  ✓ resume/, jobs.txt, applications.json and the queue script"

say "Connecting the folder to your private GitHub repo"
if [ -z "$REPO" ]; then
  REPO="$(gh api user -q .login)/internradar-private"
fi
if ! gh repo view "$REPO" >/dev/null 2>&1; then
  gh repo create "$REPO" --private --description "My InternRadar profile, CV and applications (private)" >/dev/null
  echo "  ✓ created private repo $REPO"
else
  echo "  ✓ $REPO exists"
fi
if [ "$(gh repo view "$REPO" --json visibility -q .visibility)" != "PRIVATE" ]; then
  echo "  ✗ $REPO is not private. Your CV and answers would be public; stopping here."
  exit 1
fi
URL="https://github.com/$REPO.git"
if [ ! -d "$FOLDER/.git" ]; then
  git -C "$FOLDER" init --quiet -b main
  git -C "$FOLDER" remote add origin "$URL"
fi
if git -C "$FOLDER" ls-remote --exit-code --heads origin main >/dev/null 2>&1; then
  git -C "$FOLDER" pull --quiet --rebase --autostash origin main || true
fi
git -C "$FOLDER" add -A
git -C "$FOLDER" diff --cached --quiet || git -C "$FOLDER" commit --quiet -m "Applier setup"
git -C "$FOLDER" push --quiet -u origin main
git -C "$FOLDER" config pull.rebase true
echo "  ✓ $FOLDER is linked to $REPO"

if [ -z "$(ls -A "$FOLDER/resume" 2>/dev/null)" ]; then
  echo
  echo "  → Put your CV in $FOLDER/resume/ : a Word .docx, or your Overleaf project"
  echo "    (Overleaf menu → Download → Source, then unzip it there)."
fi

say "Next steps (once)"
cat <<EOF
  1. Telegram bot: message @BotFather, send /newbot, copy the token.
  2. In a terminal run:  claude
     then inside Claude Code:
       /plugin install telegram@claude-plugins-official
       /telegram:configure <your bot token>
     and quit Claude Code.
  3. Start the applier:  $HERE/start.sh "$FOLDER"
     Send your bot any message in Telegram, it answers with a pairing code. In Claude Code run:
       /telegram:access pair <code>
       /telegram:access policy allowlist
  4. On the InternRadar site open Profile, connect $REPO with a GitHub token
     (the page explains how), fill in your profile and upload your CV there.
  5. Your numeric Telegram id: message @userinfobot.
     In GitHub (internradar → Settings → Secrets and variables → Actions) add:
       TELEGRAM_ME_BOT_TOKEN = the bot token
       TELEGRAM_CHAT_ME      = your numeric id
  6. Install the Claude in Chrome extension and sign in, and the AutoInternship extension:
       https://chromewebstore.google.com/detail/autointernship/cdfkbdkmandhnmaejaknimdhepipbpin
     Fill in its profile once and click "Download backup"; save the file as $FOLDER/profile.json

Full guide: $HERE/README.md
EOF
