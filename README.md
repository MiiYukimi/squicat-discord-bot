# 松鼠小貓 Discord Bot / Squicat Discord Bot

松鼠小貓是一個中英雙語 Discord 提醒 Bot。建立提醒後會公開確認，並在時間到時於原頻道 @ 指定對象。

Squicat is a bilingual Chinese/English Discord reminder bot. It publicly confirms reminders and mentions the selected target when due, either in the current channel or a chosen text channel.

## v0.1.0 capabilities

- Traditional Chinese / English reply selection based on the Discord client language.
- `/提醒` and `/reminder` commands.
- A reminder defaults to its creator when no target is selected. Optionally, it can target exactly one member or one role.
- `@Role` is supported.
- `@everyone` is accepted only when the command user already has Discord's **Mention @everyone, @here, and All Roles** permission.
- Real reminders: once after a duration, once at a specified Malaysia time, every X hours, every X days, and every X months.
- Private reminder list and stopping for repeating reminders.
- SQLite persistence, so reminders survive Bot restarts when the database is stored on persistent disk.
- No snooze button and no completion button.

> On Railway, attach a **Volume** mounted at `/app/data`, then set `DATABASE_PATH=/app/data/reminders.db`. Without a Volume, reminders can be lost if Railway redeploys or restarts the service.

## Setup

1. Install Python 3.11 or newer.
2. Clone this repository and enter it.
3. Create a virtual environment:

   ```bash
   python -m venv .venv
   ```

4. Activate it:

   ```bash
   # Windows PowerShell
   .venv\Scripts\Activate.ps1

   # macOS / Linux
   source .venv/bin/activate
   ```

5. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

6. Copy `.env.example` to `.env`, then paste your Bot Token into `DISCORD_TOKEN`.
7. In the Discord Developer Portal, enable **Server Members Intent** for the bot. Invite it with the `bot` and `applications.commands` scopes.
8. Start it:

   ```bash
   python -m squicat_bot
   ```

For quick testing, add your test server's numeric ID to `DEV_GUILD_ID`. Otherwise, global commands can take up to about an hour to appear.

## Commands

| Command | What it does |
| --- | --- |
| `/提醒` | Traditional Chinese entry point for creating and sending reminders. |
| `/reminder` | English entry point for creating and sending reminders. |
| `/提醒列表` / `/reminders` | Privately view reminders you created, including time until the next delivery and repeat type. |
| `/停止提醒` / `/stop_reminder` | Stop one of your own repeating reminders using the ID from the list. |

Both commands follow this order: reminder text, then one timing option, then an optional target member or role, then an optional posting channel. Fill in **exactly one** timing option: `once` (a duration such as `5h30m`), `at_time` / `指定時間` (`今天 1730`, `明天 1500`, or `YYYYMMDD HHMM`, e.g. `20260731 1500`), `every_hours`, `every_days`, or `every_months`. Specified times use Malaysia time (UTC+8). If both target fields are blank, the reminder is for the person who created it. If the posting channel is blank, the reminder is posted in the channel where the command was used.

## Project layout

```text
src/squicat_bot/
├── __main__.py       # program entry point
├── bot.py            # bot lifecycle and command synchronisation
├── i18n.py           # Chinese / English text catalogue
└── cogs/reminders.py # reminder command validation and preview
```

## Security

Never commit your `.env` file or Discord Bot Token. If a token is exposed, reset it immediately in the Discord Developer Portal.

## License

MIT. See [LICENSE](LICENSE).
