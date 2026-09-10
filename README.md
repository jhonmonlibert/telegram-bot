# Telegram AI Assistant

A lightweight, production-oriented Telegram AI assistant built for a **~1 GB RAM VPS with no GPU and no Docker**. AI inference runs remotely through **OpenRouter** (primary) with an **automatic fallback to Google Gemini / AI Studio** when the OpenRouter model is unavailable or rate-limited. No local LLM, no Redis, no PostgreSQL — just Python, `aiogram`, `httpx`, and SQLite.

---

## 1. Requirements

- Linux VPS/container, ~1 GB RAM, no GPU
- Python 3.11+
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- An [OpenRouter](https://openrouter.ai/) API key
- (Optional, recommended) A [Google AI Studio](https://aistudio.google.com/) Gemini API key, used **only as an automatic fallback**

## 2. Installation

```bash
git clone <your-repo-url> telegram_ai_bot
cd telegram_ai_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python3 run.py
```

For running tests too:

```bash
pip install -r requirements-dev.txt
python -m pytest
```

## 3. Telegram BotFather setup

1. Open a chat with [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts to choose a name and username.
3. Copy the token BotFather gives you into `TELEGRAM_BOT_TOKEN` in `.env`.
4. To use the bot in groups with a reasonable "mention" experience, you generally want **Privacy Mode** handled correctly — see section 10 below.

## 4. OpenRouter setup

1. Create an account at https://openrouter.ai/ and generate an API key.
2. Put it in `OPENROUTER_API_KEY` in `.env`.
3. Set `OPENROUTER_MODEL` to any model slug OpenRouter supports (default: `openrouter/free`).
   - OpenRouter's free models change over time and are subject to availability and rate limits — you can change the model at any time by editing `.env` and restarting the bot (`./restart.sh`), no code changes needed.

## 4b. Gemini (Google AI Studio) — automatic fallback

This bot supports Gemini as an **automatic fallback provider**: if OpenRouter fails (rate-limited, model unavailable, timeout, etc.) after its own internal retries, the same conversation is automatically retried against Gemini, transparently to the user.

1. Get a free API key at https://aistudio.google.com/.
2. Put it in `GEMINI_API_KEY` in `.env`.
3. `ENABLE_GEMINI_FALLBACK=true` (default) turns this on. Set it to `false` to disable fallback and use OpenRouter only.
4. If `GEMINI_API_KEY` is empty, the fallback is simply inactive — the bot still runs fine on OpenRouter alone.

## 5. Environment variables

See `.env.example` for the full, commented list. Key ones:

| Variable | Purpose |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from BotFather |
| `OPENROUTER_API_KEY` | OpenRouter API key |
| `OPENROUTER_MODEL` | Model slug, e.g. `openrouter/free` |
| `GEMINI_API_KEY` | Google AI Studio key (fallback) |
| `ENABLE_GEMINI_FALLBACK` | `true`/`false` |
| `ADMIN_TELEGRAM_IDS` | Comma-separated numeric Telegram user IDs |
| `DEFAULT_LANGUAGE` | `fa` or `en` |
| `MAX_HISTORY_MESSAGES` | Messages kept per conversation |
| `MAX_MESSAGE_LENGTH` | Max characters accepted from a user |
| `GROUP_MODE` | `mention` / `command` / `always` |
| `USER_RATE_LIMIT_PER_MINUTE` / `_HOUR` | Per-user limiter |
| `GROUP_RATE_LIMIT_PER_MINUTE` | Per-group limiter |
| `DATABASE_PATH` | SQLite file path |

Never commit your real `.env` file — it's already in `.gitignore`.

## 6. Running locally

```bash
source .venv/bin/activate
python3 run.py
```

Logs go to stdout and to `logs/bot.log` (rotating, secrets redacted).

## 7. Running on a VPS

```bash
git clone <your-repo-url>
cd telegram_ai_bot
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env   # fill in your tokens
python3 run.py
```

## 8. 24/7 operation without systemd

Three helper scripts are provided:

```bash
./run.sh       # starts the bot in the background with nohup, writes bot.pid
./stop.sh      # stops it gracefully (SIGTERM, then SIGKILL if needed)
./restart.sh   # stop + start, e.g. after editing .env
```

Logs land in `logs/stdout.log` and `logs/bot.log`.

If you'd like something more robust than `nohup` (auto-restart on crash, log management) without systemd, lightweight options include:

- **`tmux`/`screen`** — run `python3 run.py` inside a persistent session
- **`supervisord`** — a small Python process manager, works without systemd
- **`pm2`** (Node-based but works for any process) with `pm2 start run.py --interpreter python3`

Any of these is optional; `run.sh`/`stop.sh`/`restart.sh` work standalone.

## 9. Adding the bot to groups

1. Add your bot to the Telegram group as a member.
2. Any group member can run `/group_settings` — but only group **administrators** (or bot admins from `ADMIN_TELEGRAM_IDS`) can actually change the mode.
3. Choose a mode:
   - **mention** (default): the bot only responds when @mentioned or replied to.
   - **command**: the bot only responds to `/ask`, `/summarize`, `/translate`, `/explain`.
   - **always**: the bot processes ordinary messages too — admin opt-in only, since this means every message is sent to the AI provider.

## 10. Privacy Mode

By default, Telegram's **Privacy Mode** (configured via BotFather → `/mybots` → your bot → Bot Settings → Group Privacy) restricts what messages a bot receives in groups:

- With Privacy Mode **ON** (default), the bot only receives: commands, messages that mention it, and replies to its own messages. This is enough for `mention` and `command` modes and is the recommended, lowest-footprint setting.
- If you want `always` mode to see regular conversation (not just mentions/replies), you must turn Privacy Mode **OFF** for that bot in BotFather. Do this deliberately, and only for groups where the admin has explicitly enabled `always` mode — the bot still does not log or forward this content anywhere beyond the AI request itself.

## 11. Admin configuration

Set `ADMIN_TELEGRAM_IDS` in `.env` to a comma-separated list of numeric Telegram user IDs (use `/id` in the bot to find your own). Admins get access to:

- `/admin` — panel overview
- `/stats` — usage statistics
- `/users` / `/groups` — recent records
- `/broadcast <text>` — sends a message only to users who have started the bot and not disabled notifications, in rate-limited batches
- `/reload` — shows current runtime configuration (restart the process to actually apply `.env` changes)

## 12. Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| Bot doesn't respond at all | Check `TELEGRAM_BOT_TOKEN`; run `python3 healthcheck.py` |
| Bot replies with a generic error | OpenRouter (and Gemini, if configured) both failed — check `logs/bot.log` for the real (redacted) error |
| Bot ignores group messages | Check `GROUP_MODE` and whether Privacy Mode is blocking non-mention messages (see section 10) |
| "Model not available" behavior | OpenRouter free models rotate — change `OPENROUTER_MODEL` in `.env` and `./restart.sh` |
| High memory usage | Check `MAX_HISTORY_MESSAGES` isn't set very high; SQLite WAL files are normal and small |

## 13. Security

- Secrets (`TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`) are read only from environment variables and are never logged (a redaction filter scrubs them and `Authorization` headers from every log line).
- All admin commands re-check `ADMIN_TELEGRAM_IDS` at the handler level.
- Group settings changes require the caller to be a real Telegram group administrator (checked live via `get_chat_member`) or a configured bot admin.
- User input is sanitized (control characters stripped, length-capped) before being sent to any AI provider or stored.
- Callback data from inline keyboards is validated against a strict whitelist pattern before use.
- The bot never executes AI output or user text as shell commands or code, and never sends server secrets to any AI provider.
- `/broadcast` only reaches users who have previously started the bot and have not disabled notifications — it never messages arbitrary Telegram users.

## 14. Updating the bot

```bash
cd telegram_ai_bot
git pull
source .venv/bin/activate
pip install -r requirements.txt
./restart.sh
```

SQLite migrations run automatically on every startup (`CREATE TABLE IF NOT EXISTS ...`), so updates are safe to apply without manual DB steps.

---

## Project structure

```
telegram_ai_bot/
├── app/
│   ├── bot.py                 # Dispatcher/router wiring, startup/shutdown
│   ├── config.py               # Environment-driven configuration
│   ├── logging_config.py       # Rotating logs + secret redaction
│   ├── handlers/                # start, chat, settings, admin, groups
│   ├── services/
│   │   ├── ai_provider.py       # Shared provider interface
│   │   ├── openrouter.py        # Primary AI provider
│   │   ├── gemini.py            # Fallback AI provider
│   │   ├── ai_manager.py        # Primary→fallback orchestration
│   │   ├── conversations.py     # Bounded conversation memory
│   │   ├── users.py / groups.py
│   │   └── rate_limit.py        # In-memory sliding-window limiter
│   ├── database/                # SQLite schema + migrations
│   ├── keyboards/                # Inline keyboards
│   ├── i18n/                     # fa/en strings
│   └── utils/                    # security + text helpers
├── plugins/                      # Future plugin interface (calculator, weather, ...)
├── tests/
├── run.py / run.sh / stop.sh / restart.sh
├── healthcheck.py
├── requirements.txt / requirements-dev.txt
└── .env.example
```

## Notes on OpenRouter free models

OpenRouter's free-tier models are shared, rate-limited, and can be deprecated or swapped without notice. This project is deliberately built so that:

- Changing `OPENROUTER_MODEL` never requires touching source code.
- A failure on the primary model automatically tries Gemini (if configured), so a single provider's outage doesn't take the bot down.
- All provider errors are caught, logged, and translated into a safe, generic message for the user — raw provider errors are never shown.
