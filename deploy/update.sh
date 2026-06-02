#!/usr/bin/env bash
# deploy/update.sh — Update cv-tailor to the latest version
set -euo pipefail

INSTALL_DIR="/opt/cv-tailor"

echo "==> Updating cv-tailor..."

# 1. Move to install directory
cd "$INSTALL_DIR"

# 2. Pull latest code
echo "==> Pulling latest changes..."
git pull

# 3. Sync dependencies
echo "==> Syncing dependencies..."
uv sync

# 4. Run database migrations
echo "==> Running database migrations..."
uv run alembic upgrade head

# 5. Restart service
echo "==> Restarting cv-tailor service..."
systemctl restart cv-tailor

echo "==> Updated and restarted cv-tailor"
