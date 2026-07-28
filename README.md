# 松鼠小貓 Discord Bot / Squicat Discord Bot

松鼠小貓是一個中英雙語 Discord 提醒 Bot。v0.1.0 先提供安全的 Slash Command 骨架與提醒設定預覽；真正的排程、資料儲存與通知將在下一版本加入。

Squicat is a bilingual Chinese/English Discord reminder bot. Version 0.1.0 provides a safe Slash Command foundation and reminder setup preview. Persistent schedules and delivery will be added next.

## v0.1.0 capabilities

- Traditional Chinese / English reply selection based on the Discord client language.
- `/提醒` and `/reminder` commands.
- A reminder defaults to its creator when no target is selected. Optionally, it can target exactly one member or one role.
- `@Role` is supported.
- `@everyone` is accepted only when the command user already has Discord's **Mention @everyone, @here, and All Roles** permission.
- Supported reminder types prepared for the next phase: once, in X minutes, in X hours, daily, weekly, monthly, every X hours.
- No snooze button and no completion button.

> The v0.1.0 command only validates and previews a reminder. It deliberately does **not** send real reminders yet, so no one receives accidental notifications while the schedule database is still being built.

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
| `/提醒` | Traditional Chinese entry point for creating a reminder preview. |
| `/reminder` | English entry point for creating a reminder preview. |

Both commands follow this order: reminder text, reminder time/type, an `amount` for `in X minutes`, `in X hours`, or `every X hours`, then an optional target member or role. If both target fields are blank, the reminder is for the person who created it.

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
