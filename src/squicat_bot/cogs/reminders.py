"""Slash commands and delivery loop for Squicat reminders."""

from __future__ import annotations

import calendar
import re
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import discord
from discord import app_commands
from discord.ext import commands, tasks

from squicat_bot.i18n import language_for, text

ONCE_DURATION = re.compile(r"^\s*(?:(?P<hours>\d+)\s*h)?\s*(?:(?P<minutes>\d+)\s*m)?\s*$", re.IGNORECASE)


class ReminderCog(commands.Cog):
    """Create, persist, and deliver reminders in their original channel."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        database_path = Path(getattr(bot, "database_path", "data/reminders.db"))
        database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT, guild_id INTEGER NOT NULL, channel_id INTEGER NOT NULL,
                creator_id INTEGER NOT NULL, target_type TEXT NOT NULL, target_id INTEGER NOT NULL,
                message TEXT NOT NULL, schedule_type TEXT NOT NULL, schedule_amount INTEGER NOT NULL,
                next_run_at TEXT NOT NULL, language TEXT NOT NULL, creator_name TEXT
            )"""
        )
        columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(reminders)")}
        if "creator_name" not in columns:
            self.connection.execute("ALTER TABLE reminders ADD COLUMN creator_name TEXT")
        self.connection.commit()
        self.deliver_due_reminders.start()

    def cog_unload(self) -> None:
        self.deliver_due_reminders.cancel()
        self.connection.close()

    async def create_reminder(
        self, interaction: discord.Interaction, message: str, once: str | None,
        every_hours: int | None, every_days: int | None, every_months: int | None,
        member: discord.Member | None, role: discord.Role | None,
        post_channel: discord.TextChannel | None,
    ) -> None:
        language = language_for(interaction.locale, self.bot.default_language)
        if int(member is not None) + int(role is not None) > 1:
            await interaction.response.send_message(text(language, "too_many_targets"), ephemeral=True)
            return
        if role is not None and role.is_default() and not interaction.user.guild_permissions.mention_everyone:
            await interaction.response.send_message(text(language, "everyone_denied"), ephemeral=True)
            return
        choices = [once, every_hours, every_days, every_months]
        count = sum(value is not None for value in choices)
        if count == 0:
            await interaction.response.send_message(text(language, "schedule_required"), ephemeral=True)
            return
        if count > 1:
            await interaction.response.send_message(text(language, "only_one_schedule"), ephemeral=True)
            return

        destination = post_channel or interaction.channel
        if not isinstance(destination, discord.TextChannel):
            await interaction.response.send_message(text(language, "channel_unavailable"), ephemeral=True)
            return
        permissions = destination.permissions_for(interaction.guild.me) if interaction.guild else None
        if permissions is None or not permissions.view_channel or not permissions.send_messages:
            await interaction.response.send_message(text(language, "channel_unavailable"), ephemeral=True)
            return

        if once is not None:
            duration = self.parse_once_duration(once)
            if duration is None:
                await interaction.response.send_message(text(language, "invalid_once_duration"), ephemeral=True)
                return
            schedule_key, schedule_amount = "once", self.duration_to_minutes(duration)
            schedule_value = text(language, "once_after", duration=duration)
        elif every_hours is not None:
            schedule_key, schedule_amount = "every_hours", every_hours
            schedule_value = text(language, "every_hours", amount=every_hours)
        elif every_days is not None:
            schedule_key, schedule_amount = "every_days", every_days
            schedule_value = text(language, "every_days", amount=every_days)
        else:
            schedule_key, schedule_amount = "every_months", every_months
            schedule_value = text(language, "every_months", amount=every_months)

        target_type = "member" if member is not None else "role" if role is not None else "member"
        target_id = member.id if member is not None else role.id if role is not None else interaction.user.id
        target = member.mention if member is not None else role.mention if role is not None else interaction.user.mention
        next_run = self.next_run(schedule_key, schedule_amount)
        self.connection.execute(
            """INSERT INTO reminders (guild_id, channel_id, creator_id, target_type, target_id, message,
               schedule_type, schedule_amount, next_run_at, language, creator_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (interaction.guild_id, destination.id, interaction.user.id, target_type, target_id, message,
             schedule_key, schedule_amount, next_run.isoformat(), language, interaction.user.display_name),
        )
        self.connection.commit()

        embed = discord.Embed(title=text(language, "scheduled_title"), colour=discord.Colour.teal())
        embed.add_field(name=text(language, "field_message"), value=message, inline=False)
        embed.add_field(name=text(language, "field_type"), value=text(language, f"type_{schedule_key}"), inline=True)
        embed.add_field(name=text(language, "field_interval"), value=schedule_value, inline=True)
        embed.add_field(name=text(language, "field_target"), value=target, inline=True)
        embed.add_field(name=text(language, "field_channel"), value=destination.mention, inline=True)
        embed.set_footer(text=text(language, "scheduled_notice"))
        await interaction.response.send_message(embed=embed)

    @staticmethod
    def parse_once_duration(value: str) -> str | None:
        match = ONCE_DURATION.fullmatch(value)
        if match is None or (match.group("hours") is None and match.group("minutes") is None):
            return None
        hours, minutes = int(match.group("hours") or 0), int(match.group("minutes") or 0)
        if hours == 0 and minutes == 0:
            return None
        return f"{hours}h{minutes}m" if hours and minutes else f"{hours}h" if hours else f"{minutes}m"

    @staticmethod
    def duration_to_minutes(value: str) -> int:
        match = ONCE_DURATION.fullmatch(value)
        assert match is not None
        return int(match.group("hours") or 0) * 60 + int(match.group("minutes") or 0)

    @staticmethod
    def next_run(schedule_type: str, amount: int, from_time: datetime | None = None) -> datetime:
        now = from_time or datetime.now(UTC)
        if schedule_type == "once":
            return now + timedelta(minutes=amount)
        if schedule_type == "every_hours":
            return now + timedelta(hours=amount)
        if schedule_type == "every_days":
            return now + timedelta(days=amount)
        month = now.month - 1 + amount
        year, month = now.year + month // 12, month % 12 + 1
        return now.replace(year=year, month=month, day=min(now.day, calendar.monthrange(year, month)[1]))

    @tasks.loop(seconds=20)
    async def deliver_due_reminders(self) -> None:
        due = self.connection.execute(
            "SELECT * FROM reminders WHERE next_run_at <= ? ORDER BY next_run_at", (datetime.now(UTC).isoformat(),)
        ).fetchall()
        for reminder in due:
            await self._deliver(reminder)

    @deliver_due_reminders.before_loop
    async def before_deliver_due_reminders(self) -> None:
        await self.bot.wait_until_ready()

    async def _deliver(self, reminder: sqlite3.Row) -> None:
        channel = self.bot.get_channel(reminder["channel_id"])
        if not isinstance(channel, discord.abc.Messageable):
            return
        guild = self.bot.get_guild(reminder["guild_id"])
        # A guild member may not be in discord.py's cache after a Railway
        # restart.  Raw Discord mention syntax is stable and still pings the
        # original ID, so do not treat a cache miss as a missing recipient.
        target = (
            f"<@&{reminder['target_id']}>"
            if reminder["target_type"] == "role"
            else f"<@{reminder['target_id']}>"
        )
        language = reminder["language"]
        embed = discord.Embed(
            title=text(language, "delivery_title"),
            description=reminder["message"],
            colour=discord.Colour(0xFFED8D),
        )
        creator_name = reminder["creator_name"]
        if not creator_name and guild is not None:
            creator = guild.get_member(reminder["creator_id"])
            if creator is None:
                try:
                    creator = await guild.fetch_member(reminder["creator_id"])
                except discord.HTTPException:
                    creator = None
            creator_name = creator.display_name if creator else "Unknown"
        embed.set_footer(text=text(language, "delivery_footer", creator=creator_name or "Unknown"))
        try:
            await channel.send(
                content=target,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(users=True, roles=True, everyone=True),
            )
        except discord.HTTPException:
            return
        if reminder["schedule_type"] == "once":
            self.connection.execute("DELETE FROM reminders WHERE id = ?", (reminder["id"],))
        else:
            start = datetime.fromisoformat(reminder["next_run_at"])
            new_next = self.next_run(reminder["schedule_type"], reminder["schedule_amount"], start)
            self.connection.execute("UPDATE reminders SET next_run_at = ? WHERE id = ?", (new_next.isoformat(), reminder["id"]))
        self.connection.commit()

    @staticmethod
    def _target_mention(reminder: sqlite3.Row) -> str:
        """Return a stable Discord mention without relying on the member cache."""
        if reminder["target_type"] == "role":
            return f"<@&{reminder['target_id']}>"
        return f"<@{reminder['target_id']}>"

    @staticmethod
    def _short_message(value: str, limit: int = 100) -> str:
        """Keep a list entry readable while preserving the original reminder."""
        compact = " ".join(value.split())
        return compact if len(compact) <= limit else f"{compact[:limit - 1]}…"

    @staticmethod
    def _remaining_time(next_run_at: str, language: str) -> str:
        """Format the delay until the next delivery in the user's language."""
        seconds = max(0, int((datetime.fromisoformat(next_run_at) - datetime.now(UTC)).total_seconds()))
        days, seconds = divmod(seconds, 86_400)
        hours, seconds = divmod(seconds, 3_600)
        minutes = (seconds + 59) // 60
        if language == "zh":
            parts = [f"{days} 天" if days else "", f"{hours} 小時" if hours else "", f"{minutes} 分鐘" if minutes else ""]
            return " ".join(part for part in parts if part) or "不到 1 分鐘"
        parts = [f"{days}d" if days else "", f"{hours}h" if hours else "", f"{minutes}m" if minutes else ""]
        return " ".join(part for part in parts if part) or "under 1m"

    def _schedule_value(self, reminder: sqlite3.Row, language: str) -> str:
        if reminder["schedule_type"] == "once":
            return text(language, "once_after", duration=self._remaining_time(reminder["next_run_at"], language))
        return text(language, reminder["schedule_type"], amount=reminder["schedule_amount"])

    async def list_reminders(self, interaction: discord.Interaction) -> None:
        """Show the invoking user's pending reminders without exposing them publicly."""
        language = language_for(interaction.locale, self.bot.default_language)
        rows = self.connection.execute(
            """SELECT * FROM reminders WHERE creator_id = ? AND next_run_at > ?
               ORDER BY next_run_at ASC LIMIT 10""",
            (interaction.user.id, datetime.now(UTC).isoformat()),
        ).fetchall()
        if not rows:
            await interaction.response.send_message(text(language, "list_empty"), ephemeral=True)
            return

        embed = discord.Embed(title=text(language, "list_title"), colour=discord.Colour.teal())
        embed.description = "\n\n".join(
            text(
                language,
                "list_item",
                id=row["id"],
                message=self._short_message(row["message"]),
                remaining=self._remaining_time(row["next_run_at"], language),
                schedule=self._schedule_value(row, language),
                target=self._target_mention(row),
                channel=f"<#{row['channel_id']}>",
            )
            for row in rows
        )
        embed.set_footer(text=text(language, "list_footer"))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def stop_repeating_reminder(self, interaction: discord.Interaction, reminder_id: int) -> None:
        """Stop only a repeating reminder created by the invoking user."""
        language = language_for(interaction.locale, self.bot.default_language)
        reminder = self.connection.execute(
            "SELECT * FROM reminders WHERE id = ? AND creator_id = ?", (reminder_id, interaction.user.id)
        ).fetchone()
        if reminder is None:
            await interaction.response.send_message(text(language, "cancel_not_found"), ephemeral=True)
            return
        if reminder["schedule_type"] == "once":
            await interaction.response.send_message(text(language, "cancel_once", id=reminder_id), ephemeral=True)
            return
        self.connection.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        self.connection.commit()
        embed = discord.Embed(title=text(language, "cancelled_title"), colour=discord.Colour.teal())
        embed.description = text(language, "cancelled_message", id=reminder_id, message=self._short_message(reminder["message"]))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="reminder", description="Create and send a reminder.")
    @app_commands.describe(message="What should Squicat remind them about?", once="Once only, e.g. 5h30m.", every_hours="Repeat every X hours.", every_days="Repeat every X days.", every_months="Repeat every X months.", member="Optional member; leave blank for yourself.", role="Optional role; leave blank for yourself.", post_channel="Optional channel to post the reminder in; leave blank for this channel.")
    async def reminder(self, interaction: discord.Interaction, message: app_commands.Range[str, 1, 1000], once: str | None = None, every_hours: app_commands.Range[int, 1, 8760] | None = None, every_days: app_commands.Range[int, 1, 8760] | None = None, every_months: app_commands.Range[int, 1, 8760] | None = None, member: discord.Member | None = None, role: discord.Role | None = None, post_channel: discord.TextChannel | None = None) -> None:
        await self.create_reminder(interaction, message, once, every_hours, every_days, every_months, member, role, post_channel)

    @app_commands.guild_only()
    @app_commands.command(name="提醒", description="建立並送出提醒。")
    @app_commands.rename(once="一次", every_hours="每x小時", every_days="每x天", every_months="每x個月", post_channel="發佈頻道")
    @app_commands.describe(message="想提醒對方什麼？", once="一次提醒；填寫時間，例如 5h30m。", every_hours="每 X 小時提醒一次；直接填 X。", every_days="每 X 天提醒一次；直接填 X。", every_months="每 X 個月提醒一次；直接填 X。", member="選填；留空就提醒自己，否則選擇一位成員。", role="選填；留空就提醒自己，否則選擇一個身分組；有權限時可選 @everyone。", post_channel="選填；指定提醒要發佈的文字頻道，留空就是目前頻道。")
    async def reminder_chinese(self, interaction: discord.Interaction, message: app_commands.Range[str, 1, 1000], once: str | None = None, every_hours: app_commands.Range[int, 1, 8760] | None = None, every_days: app_commands.Range[int, 1, 8760] | None = None, every_months: app_commands.Range[int, 1, 8760] | None = None, member: discord.Member | None = None, role: discord.Role | None = None, post_channel: discord.TextChannel | None = None) -> None:
        await self.create_reminder(interaction, message, once, every_hours, every_days, every_months, member, role, post_channel)

    @app_commands.guild_only()
    @app_commands.command(name="reminders", description="View your active and scheduled reminders.")
    async def reminders(self, interaction: discord.Interaction) -> None:
        await self.list_reminders(interaction)

    @app_commands.guild_only()
    @app_commands.command(name="提醒列表", description="查看你目前進行中與排程中的提醒。")
    async def reminders_chinese(self, interaction: discord.Interaction) -> None:
        await self.list_reminders(interaction)

    @app_commands.guild_only()
    @app_commands.command(name="stop_reminder", description="Stop one of your repeating reminders using its ID.")
    @app_commands.describe(reminder_id="The reminder ID shown in /reminders.")
    async def stop_reminder(self, interaction: discord.Interaction, reminder_id: app_commands.Range[int, 1]) -> None:
        await self.stop_repeating_reminder(interaction, reminder_id)

    @app_commands.guild_only()
    @app_commands.command(name="停止提醒", description="使用編號停止你設定的重複提醒。")
    @app_commands.rename(reminder_id="提醒編號")
    @app_commands.describe(reminder_id="在 /提醒列表 顯示的提醒編號。")
    async def stop_reminder_chinese(self, interaction: discord.Interaction, reminder_id: app_commands.Range[int, 1]) -> None:
        await self.stop_repeating_reminder(interaction, reminder_id)
