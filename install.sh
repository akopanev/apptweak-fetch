#!/usr/bin/env bash
set -euo pipefail

REPO="https://github.com/akopanev/apptweak-fetch.git"
DIR="${1:-$(pwd)/.apptweak}"
API_KEY="${2:-}"

echo "Installing apptweak-fetch to $DIR ..."

if [ -d "$DIR" ]; then
  echo "Directory $DIR already exists. Updating..."
  git -C "$DIR" pull --ff-only
else
  git clone "$REPO" "$DIR"
fi

echo "Setting up Python venv..."
python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -q -r "$DIR/requirements.txt"

if [ -n "$API_KEY" ]; then
  echo "APPTWEAK_API_KEY=$API_KEY" > "$DIR/.env"
  echo "API key saved."
elif [ ! -f "$DIR/.env" ]; then
  cp "$DIR/.env.example" "$DIR/.env"
  echo ""
  echo ">>> Edit $DIR/.env and add your AppTweak API key <<<"
  echo ""
fi

# Add .apptweak to parent .gitignore if it exists or is a git repo
PARENT="$(dirname "$DIR")"
BASENAME="$(basename "$DIR")"
if [ -d "$PARENT/.git" ] || git -C "$PARENT" rev-parse --git-dir > /dev/null 2>&1; then
  if ! grep -qxF "$BASENAME/" "$PARENT/.gitignore" 2>/dev/null; then
    echo "$BASENAME/" >> "$PARENT/.gitignore"
    echo "Added $BASENAME/ to $PARENT/.gitignore"
  fi
fi

echo "Done! Usage:"
echo "  $DIR/fetch.sh \"keyword1,keyword2,keyword3\""
