# Telegram Gifts Autoscoop (Bot + Userbot)

This repository contains a bot that automatically buys newly released Telegram gifts as soon as they appear. It supports two modes:

- Bot API — purchases are made on behalf of the bot
- Userbot (personal account via Telethon) — purchases are made on behalf of your account, including premium gifts

The new gifts detector is based on the project https://github.com/arynyklas/tg_gifts_notifier. Everything unnecessary was removed; the logic for fetching/storing the gifts catalog and wrappers for autoscoop were kept.


## Features

- Detect new gifts via Pyrogram (`detector.py`)
- Notify bot users about new gifts
- Flexible orders by price/quantity and budget
- Auto-purchase:
  - via Bot API (default)
  - via personal account (Telethon) — useful when Bot API fails or for premium gifts
- Link a personal account in the bot interface
- MongoDB storage for users, orders, and accounts


## Requirements

- Python 3.11+
- MongoDB (local or cloud)

Install dependencies:

```bash
pip install -r requirements.txt
```

Note: detector dependencies — `pyrogram`, `pytz`.


## Configuration

The project uses two configs: the root `config.py` and `bot/config.py`.

### Root `config.py`
File: `config.py`

Fields:
- `SESSION_NAME` — Pyrogram session name for the detector (stored under `sessions/`).
- `API_ID`, `API_HASH` — Telegram app credentials for the Pyrogram client.
- `CHECK_INTERVAL` — polling interval for the gifts catalog (seconds).
- `TIMEZONE` — logging timezone (e.g., `UTC`).
- `DATA_FILEPATH` — path to gifts data file (default `gifts_data/star_gifts.json`).
- Console/file log levels.

Where to get `API_ID` and `API_HASH`:
1. Go to https://my.telegram.org
2. Log in with your account
3. Open “API Development Tools”
4. Create an app and copy `api_id` and `api_hash`

On the first detector launch, Pyrogram will create a session (`sessions/SESSION_NAME.session`) and may ask for phone/2FA code in the console.

### Bot config `bot/config.py`
File: `bot/config.py`

Fields:
- `BOT_TOKEN` — Telegram bot token (from @BotFather)
- `MONGO_URL` — MongoDB connection string (default local `mongodb://127.0.0.1:27017`)
- `DB_NAME` — database name (default `autoscoop`)
- `TELETHON_API_ID`, `TELETHON_API_HASH` — credentials for Telethon (can be the same as root config)
- `DEV_USER_ID` — your Telegram ID (admin)
- `TAKE_COMMISSION` — whether to take commission on top-ups (if you are the only user — set `False`)


## Run

Open two terminals in the project root.

1) New gifts detector (Pyrogram):
```bash
python detector.py
```
- On first run, authorization and session creation happen under `sessions/`.
- The detector polls the gifts catalog and, on new gift detection, passes the event to autoscoop (`autoscoop.process_new_gift_for_autoscoop`).

2) Management and autoscoop bot (Aiogram):
```bash
python -m bot.main
```
- In Telegram, find your bot and run `/start`.
- In the settings menu you can:
  - top up balance
  - create/enable orders (price/limits/budget/target channel)
  - link a personal account (Telethon) for personal purchases


## How purchasing works

- When a new gift appears, all users with active orders receive a notification.
- For each user, the bot checks balance, price/supply bounds, order budget, and available gift limits.
- Purchases follow this priority:
  1. If the gift is premium — it can only be purchased via a personal account (if linked and premium flag is allowed).
  2. If “only personal purchases” is enabled — purchase goes through Telethon.
  3. Otherwise, try via Bot API. If it fails (errors/restrictions), a fallback to the personal account is possible if it’s linked and allowed.
- All balance and order budget updates are stored in MongoDB.

Key files:
- `detector.py` — starts Pyrogram client and tracks new gifts
- `autoscoop.py` — handles new gifts and purchases (Bot API / Telethon)
- `bot/main.py` — entry point for the Aiogram bot
- `bot/utils/telethon_client.py` — utilities for linking and buying via personal account


## MongoDB

- By default, `MONGO_URL=mongodb://127.0.0.1:27017` and database `autoscoop`.
- Collections are created automatically on first use.


## Tips

- Keep both processes (detector and bot) running concurrently.
- Premium gifts require a linked account with Telegram Premium.
- To avoid Bot API limitations, use personal account purchases.


## License and credits

- Gifts detector base from: https://github.com/arynyklas/tg_gifts_notifier
- Author: @dark_qubit
- Channel: https://t.me/dq_devlog
- Support the author (TON): `UQCqI9aG0_BHHSp7-GMMpJuJ4PH84OdT0T1cl_dbUWifcPys`
