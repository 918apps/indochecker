# Skiddle-ID Trust+ Positif Monitor Bot

A free Telegram bot that monitors your domains against **ALL** .txt files in the [Skiddle-ID/blocklist](https://github.com/Skiddle-ID/blocklist) repo (Kominfo's blocked domains/IPs).

## Features
- `/add example.com` — Start monitoring a domain
- `/remove example.com` — Stop monitoring
- `/list` — Show your domains + statuses
- `/status` — Force check now
- `/pause` — Pause hourly alerts
- `/resume` — Resume hourly alerts
- Alerts **only** on status changes (BLOCKED → CLEAN or vice versa)
- Hourly auto-refresh of full blocklist (~1-2M entries)

## Deploy for Free (Oracle Cloud Always Free)
1. Sign up at [oracle.com/cloud/free](https://www.oracle.com/cloud/free) (no CC needed).
2. Create Ubuntu VM (Ampere A1, any region).
3. SSH in & run:
