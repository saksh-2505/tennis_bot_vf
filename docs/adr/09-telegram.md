# ADR 9: Telegram — Why Polling Bot

## Problem
Need interactive bot for querying match data and receiving incident alerts.

## Decision
Polling-based Telegram bot (monitor container polls `getUpdates` every 60s) + direct notification via `sendMessage`.

## Alternatives
- **Webhook-based bot**: Requires public HTTPS endpoint; more complex deployment
- **Long polling only**: Simpler; works behind NAT
- **Dedicated bot process**: Extra container; harder to coordinate with incident flow

## Tradeoffs
- + Long polling is simple HTTP GET — no persistent connections
- + Runs inside the incident monitor container (no separate deployment)
- + 60s interval is acceptable for query-style commands
- - 60s latency between user command and response
- - No webhook means missed events if server is down
- - `/tmp/telegram_offset` file resets on container restart

## Consequences
- Bot runs in `incidents/telegram_bot.py` (monitor container)
- 23 command handlers organized by domain (matches, players, live, system)
- HTML parse mode with manual escaping for safety
- Offset management prevents duplicate processing
