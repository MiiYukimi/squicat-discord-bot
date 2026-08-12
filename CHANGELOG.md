# Changelog

## [0.2.0] - 2026-07-29

### Added

- Public confirmation when a reminder is created.
- Actual reminder delivery in the original channel, including the selected member or role mention.
- SQLite reminder storage and a Railway Volume configuration option.

## [Unreleased]

- Add owner-only `/代發` and `/say`: write a message privately, select a text channel, and let Squicat post it without sender attribution.
- Allow `指定時間` / `at_time` to be combined with a repeating schedule as its first delivery time.
- Replace the type picker and `amount` field with four direct timing fields: once (`5h30m`), every X hours, every X days, or every X months.
- Validate that each reminder has exactly one timing field.

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-07-28

### Added

- Python `discord.py` project foundation.
- Traditional Chinese and English reply system.
- Initial `/提醒` and `/reminder` Slash Commands, including target validation.
- `.env.example`, dependency list, and local development guidance.

### Not yet included

- Persistent reminder storage and scheduled delivery.
- Recurrence calculation for daily, weekly, monthly, and every-X-hours reminders.
