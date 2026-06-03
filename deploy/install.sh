#!/usr/bin/env bash
# deploy/install.sh — Idempotent install script for cv-tailor on Debian/Ubuntu LXC
set -euo pipefail

REPO_URL="https://github.com/mrafik92/cv-updater"
INSTALL_DIR="/opt/cv-tailor"
SERVICE_FILE="deploy/cv-tailor.service"

echo "==> Installing cv-tailor..."

# 1. Clone repo or update if already present
if [ -d "$INSTALL_DIR/.git" ]; then
    echo "==> $INSTALL_DIR already exists — pulling latest changes..."
    git -C "$INSTALL_DIR" pull
else
    echo "==> Cloning repository to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# 2. Install uv if not present
if ! command -v uv &>/dev/null; then
    echo "==> Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add uv to PATH for this session
    export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
fi

# 3. Sync Python dependencies
echo "==> Installing Python dependencies with uv..."
uv sync

# 4. Install Playwright Chromium
echo "==> Installing Playwright Chromium..."
uv run playwright install chromium --with-deps

# 5. Set up .env if not present
if [ ! -f ".env" ]; then
    echo "==> Creating .env from .env.example..."
    cp .env.example .env
    chmod 600 .env
    echo ""
    echo "  *** ACTION REQUIRED ***"
    echo "  Edit $INSTALL_DIR/.env and fill in your secrets before proceeding:"
    echo "    - OPENROUTER_API_KEY"
    echo "    - RR_BASE_URL"
    echo "    - RR_API_TOKEN"
    echo "  Then re-run this script or start the service manually."
    echo ""
else
    echo "==> .env already exists, skipping."
fi

# 6. Run database migrations
echo "==> Running database migrations..."
uv run alembic upgrade head

# 7. Install systemd unit
echo "==> Installing systemd unit..."
cp "$SERVICE_FILE" /etc/systemd/system/cv-tailor.service

# 8. Enable and start service
echo "==> Enabling and starting cv-tailor service..."
systemctl daemon-reload
systemctl enable --now cv-tailor

echo ""
echo "==> cv-tailor installed successfully!"
echo "    Service: http://127.0.0.1:8000"
echo "    Logs:    journalctl -u cv-tailor -f"
