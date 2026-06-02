# CV Tailor

A resume tailoring web app that generates customised resumes using LLMs and Reactive Resume.

---

## Prerequisites

- Debian/Ubuntu LXC (or compatible VM)
- Python 3.12+
- `git`
- Internet access (for cloning repo, installing dependencies, and calling OpenRouter/Reactive Resume APIs)
- ~500 MB free disk space

---

## Install

Run the install script as `root` (or with `sudo`):

```bash
git clone https://github.com/mrafik/cv-updater /opt/cv-tailor
cd /opt/cv-tailor
bash deploy/install.sh
```

The script will:

1. Create the `cvtailor` system user
2. Clone the repo to `/opt/cv-tailor` (or `git pull` if already present)
3. Install `uv` (Python package manager) if not found
4. Install Python dependencies via `uv sync`
5. Install Playwright Chromium for PDF generation
6. Copy `.env.example` → `.env` if no `.env` exists (you must fill in secrets — see [Configuration](#configuration))
7. Run database migrations (`alembic upgrade head`)
8. Install and enable the `cv-tailor` systemd unit

After install, the app is available at `http://127.0.0.1:8000`.

---

## Configuration

All configuration is via environment variables in `/opt/cv-tailor/.env`.

| Variable | Description | Example |
|---|---|---|
| `APP_HOST` | Host the app binds to | `127.0.0.1` |
| `APP_PORT` | Port the app listens on | `8000` |
| `DATABASE_URL` | SQLite database URL | `sqlite:///data/cv_tailor.db` |
| `OPENROUTER_API_KEY` | OpenRouter API key for LLM access | `sk-or-v1-...` |
| `OPENROUTER_MODEL` | LLM model identifier | `anthropic/claude-sonnet-4.5` |
| `OPENROUTER_BASE_URL` | OpenRouter API base URL | `https://openrouter.ai/api/v1` |
| `RR_BASE_URL` | Reactive Resume instance base URL | `http://10.0.0.5:3000` |
| `RR_API_TOKEN` | Reactive Resume API token | `ey...` |
| `LOG_LEVEL` | Application log verbosity | `INFO` |
| `PDF_TIMEOUT_SECONDS` | PDF generation timeout in seconds | `60` |

Edit `/opt/cv-tailor/.env` and set at minimum:

```bash
OPENROUTER_API_KEY=your-key-here
RR_BASE_URL=http://<your-reactive-resume-host>:3000
RR_API_TOKEN=your-token-here
```

Then restart the service:

```bash
systemctl restart cv-tailor
```

---

## Update

```bash
bash /opt/cv-tailor/deploy/update.sh
```

This pulls the latest code, syncs dependencies, runs any new migrations, and restarts the service.

---

## Logs

```bash
journalctl -u cv-tailor -f
```

---

## Troubleshooting

**Port 8000 already in use**

Check what is using the port and stop it, or change `APP_PORT` in `.env` and update `ExecStart` in the systemd unit accordingly.

```bash
ss -tlnp | grep 8000
```

**Missing or invalid env vars**

If the app fails to start, check the logs for `ValidationError` or `missing` messages. Ensure all required values in `/opt/cv-tailor/.env` are set and the file is readable by the `cvtailor` user (`chmod 600 /opt/cv-tailor/.env`).

**Playwright / Chromium dependency errors**

Re-run the Playwright install step:

```bash
cd /opt/cv-tailor && uv run playwright install chromium --with-deps
```

On minimal Debian containers you may need to install additional system packages:

```bash
apt-get install -y libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1
```

**Database migration failures**

Check the migration output manually:

```bash
cd /opt/cv-tailor && uv run alembic upgrade head
```

If migrations are in a broken state, inspect `alembic_version` in the database or check `migrations/` for conflicts.

**Service fails to start after install**

```bash
systemctl status cv-tailor
journalctl -u cv-tailor --no-pager -n 50
```

Ensure `/opt/cv-tailor` and its contents are owned by `cvtailor`:

```bash
chown -R cvtailor:cvtailor /opt/cv-tailor
```
