#!/usr/bin/env bash
# Download Tailwind standalone CLI (linux-x64) into ./tailwindcss
set -euo pipefail

URL="https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64"
DEST="./tailwindcss"

if [ -x "$DEST" ]; then
  echo "Tailwind CLI already present at $DEST"
  exit 0
fi

echo "Downloading Tailwind standalone CLI..."
curl -sLfo "$DEST" "$URL"
chmod +x "$DEST"
echo "Installed: $($DEST --help 2>&1 | head -n 1 || echo $DEST)"
