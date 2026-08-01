"""Slash commands and delivery loop for Squicat reminders."""

from __future__ import annotations

import calendar
import re
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands, tasks

from squicat_bot.i18n import language_for, text

ONCE_DURATION = re.compile(r"^\s*(?:(?P<hours>\d+)\s*h)?\s*(?:(?P<minutes>\d+)\s*m)?\s*$", re.IGNORECASE)
SPECIFIC_TIME = re.compile(r"^\s*(?P<date>today|tomorrow|今天|明天|\d{8})\s+(?P<time>\d{4})\s*$", re.IGNORECASE)
MALAYSIA_TIMEZONE = ZoneInfo("Asia/Kuala_Lumpur")


@dataclass
class ReminderDraft:
    """Short-lived state for the guided reminder creation flow."""

    creator_id: int
    language: str
    message: str
    schedule_key: str | None = None
    schedule_amount: int | None = None
    next_run: datetime | None = None
    schedule_value: str | None = None
    first_run_value: str | None = None
    post_channel: discord.TextChannel | None = None


def ui_text(language: str, chinese: str, english: str) -> str:
    return chinese if language == "zh" else english


class OwnerView(discord.ui.View):
    """A view that can only be completed by the person who started it."""

    def __init__(self, cog: "ReminderCog", draft: ReminderDraft) -> None:
        super().__init__(timeout=600)
        self.cog, self.draft = cog, draft

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.draft.creator_id:
            return True
        await interaction.response.send_message(
            ui_text(self.draft.language, "這個提醒設定不是你的喔。", "This reminder setup belongs to someone else."),
            ephemeral=True,
        )
        return False

    async def on_timeout(self) -> None:
        for child in self.children:
            child.disabled = True


class MessageModal(discord.ui.Modal):
    def __init__(self, cog: "ReminderCog", language: str) -> None:
        super().__init__(title=ui_text(language, "① 提醒訊息", "1. Reminder message"))
        self.cog, self.language = cog, language
        self.message_input = discord.ui.TextInput(
            label=ui_text(language, "想提醒什麼？", "What should Squicat remind them about?"),
            style=discord.TextStyle.paragraph,
            max_length=1000,
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        draft = ReminderDraft(interaction.user.id, self.language, self.message_input.value.strip())
        await interaction.response.send_message(
            ui_text(self.language, "② 選擇提醒時間／循環方式", "2. Choose timing / repeat type"),
            view=ScheduleView(self.cog, draft),
            ephemeral=True,
        )


class ScheduleSelect(discord.ui.Select):
    def __init__(self, cog: "ReminderCog", draft: ReminderDraft) -> None:
        self.cog, self.draft = cog, draft
        language = draft.language
        super().__init__(
            placeholder=ui_text(language, "選擇一種提醒方式", "Choose one reminder type"),
            options=[
                discord.SelectOption(label=ui_text(language, "一次：多久後", "Once: after a duration"), value="once"),
                discord.SelectOption(label=ui_text(language, "一次：指定時間", "Once: at a specific time"), value="at_time"),
                discord.SelectOption(label=ui_text(language, "每 X 小時", "Every X hours"), value="every_hours"),
                discord.SelectOption(label=ui_text(language, "每 X 天", "Every X days"), value="every_days"),
                discord.SelectOption(label=ui_text(language, "每 X 個月", "Every X months"), value="every_months"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        schedule_key = self.values[0]
        if schedule_key in {"every_hours", "every_days", "every_months"}:
            await interaction.response.send_modal(RepeatAmountModal(self.cog, self.draft, schedule_key))
        else:
            await interaction.response.send_modal(OneTimeModal(self.cog, self.draft, schedule_key))


class ScheduleView(OwnerView):
    def __init__(self, cog: "ReminderCog", draft: ReminderDraft) -> None:
        super().__init__(cog, draft)
        self.add_item(ScheduleSelect(cog, draft))


class OneTimeModal(discord.ui.Modal):
    def __init__(self, cog: "ReminderCog", draft: ReminderDraft, schedule_key: str) -> None:
        language = draft.language
        title = ui_text(language, "② 設定一次提醒", "2. Set one-time reminder")
        super().__init__(title=title)
        self.cog, self.draft, self.schedule_key = cog, draft, schedule_key
        specific = schedule_key == "at_time"
        self.value_input = discord.ui.TextInput(
            label=ui_text(language, "提醒時間", "Reminder time") if specific else ui_text(language, "多久後提醒？", "Remind after how long?"),
            placeholder=(ui_text(language, "今天 1730／明天 1500／20260805 0900", "today 1730 / tomorrow 1500 / 20260805 0900") if specific else "5h30m"),
            max_length=30,
        )
        self.add_item(self.value_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if self.schedule_key == "once":
            duration = self.cog.parse_once_duration(self.value_input.value)
            if duration is None:
                await interaction.response.send_message(text(self.draft.language, "invalid_once_duration"), ephemeral=True)
                return
            self.draft.schedule_key, self.draft.schedule_amount = "once", self.cog.duration_to_minutes(duration)
            self.draft.next_run = self.cog.next_run("once", self.draft.schedule_amount)
            self.draft.schedule_value = text(self.draft.language, "once_after", duration=duration)
        else:
            specified_run = self.cog.parse_specific_time(self.value_input.value)
            if specified_run is None:
                await interaction.response.send_message(text(self.draft.language, "invalid_specific_time"), ephemeral=True)
                return
            self.draft.schedule_key, self.draft.schedule_amount, self.draft.next_run = "once", 0, specified_run
            self.draft.schedule_value = text(self.draft.language, "once_at", time=self.cog.format_malaysia_time(specified_run, self.draft.language))
        await self.cog.show_channel_step(interaction, self.draft)


class RepeatAmountModal(discord.ui.Modal):
    def __init__(self, cog: "ReminderCog", draft: ReminderDraft, schedule_key: str) -> None:
        super().__init__(title=ui_text(draft.language, "② 填寫循環間隔", "2. Enter repeat interval"))
        self.cog, self.draft, self.schedule_key = cog, draft, schedule_key
        labels = {
            "every_hours": ui_text(draft.language, "每幾小時提醒一次？", "Repeat every how many hours?"),
            "every_days": ui_text(draft.language, "每幾天提醒一次？", "Repeat every how many days?"),
            "every_months": ui_text(draft.language, "每幾個月提醒一次？", "Repeat every how many months?"),
        }
        self.amount_input = discord.ui.TextInput(label=labels[schedule_key], placeholder="例如：1", max_length=4)
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            amount = int(self.amount_input.value.strip())
        except ValueError:
            amount = 0
        if not 1 <= amount <= 8760:
            await interaction.response.send_message(ui_text(self.draft.language, "請填寫 1 至 8760 的整數。", "Enter a whole number from 1 to 8760."), ephemeral=True)
            return
        self.draft.schedule_key, self.draft.schedule_amount = self.schedule_key, amount
        self.draft.schedule_value = text(self.draft.language, self.schedule_key, amount=amount)
        # Discord does not permit opening a second modal as the direct response
        # to a modal submission.  Use one small interstitial button instead;
        # its button interaction can legally open the time-entry modal.
        await interaction.response.send_message(
            ui_text(
                self.draft.language,
                f"已設定 {self.draft.schedule_value}。接著填寫第一次提醒時間。",
                f"Set to {self.draft.schedule_value}. Next, enter the first reminder time.",
            ),
            view=FirstRunView(self.cog, self.draft),
            ephemeral=True,
        )


class FirstRunView(OwnerView):
    """A legal bridge between the repeat-amount and first-run modals."""

    @discord.ui.button(label="填寫第一次提醒時間", style=discord.ButtonStyle.primary, emoji="🕒")
    async def enter_first_time(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_modal(FirstRunModal(self.cog, self.draft))


class FirstRunModal(discord.ui.Modal):
    def __init__(self, cog: "ReminderCog", draft: ReminderDraft) -> None:
        super().__init__(title=ui_text(draft.language, "② 設定第一次提醒時間", "2. Set first reminder time"))
        self.cog, self.draft = cog, draft
        self.time_input = discord.ui.TextInput(
            label=ui_text(draft.language, "第一次什麼時候提醒？", "When should the first reminder be?"),
            placeholder=ui_text(draft.language, "今天 1730／明天 1500／20260805 0900", "today 1730 / tomorrow 1500 / 20260805 0900"),
            max_length=30,
        )
        self.add_item(self.time_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        specified_run = self.cog.parse_specific_time(self.time_input.value)
        if specified_run is None:
            await interaction.response.send_message(text(self.draft.language, "invalid_specific_time"), ephemeral=True)
            return
        self.draft.next_run = specified_run
        self.draft.first_run_value = self.cog.format_malaysia_time(specified_run, self.draft.language)
        await self.cog.show_channel_step(interaction, self.draft)


class ChannelSelect(discord.ui.ChannelSelect):
    def __init__(self, cog: "ReminderCog", draft: ReminderDraft) -> None:
        self.cog, self.draft = cog, draft
        super().__init__(
            placeholder=ui_text(draft.language, "選擇發佈提醒的頻道", "Choose the channel to post in"),
            channel_types=[discord.ChannelType.text],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        # ChannelSelect returns an AppCommandChannel during an interaction,
        # rather than a discord.TextChannel.  Resolve it through the guild
        # cache/API before validating permissions.
        channel = await self.cog.resolve_post_channel(interaction, self.values[0].id)
        if channel is None:
            await interaction.response.send_message(text(self.draft.language, "channel_unavailable"), ephemeral=True)
            return
        self.draft.post_channel = channel
        await interaction.response.edit_message(
            content=ui_text(self.draft.language, "④ 選擇提醒對象", "4. Choose who to remind"),
            view=TargetView(self.cog, self.draft),
        )


class ChannelView(OwnerView):
    def __init__(self, cog: "ReminderCog", draft: ReminderDraft) -> None:
        super().__init__(cog, draft)
        self.add_item(ChannelSelect(cog, draft))


class TargetSelect(discord.ui.MentionableSelect):
    def __init__(self, cog: "ReminderCog", draft: ReminderDraft) -> None:
        self.cog, self.draft = cog, draft
        super().__init__(placeholder=ui_text(draft.language, "選擇一位成員或一個身分組", "Choose one member or role"), min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction) -> None:
        chosen = self.values[0]
        await self.cog.finalize_draft(interaction, self.draft, chosen if isinstance(chosen, discord.Member) else None, chosen if isinstance(chosen, discord.Role) else None)


class TargetView(OwnerView):
    def __init__(self, cog: "ReminderCog", draft: ReminderDraft) -> None:
        super().__init__(cog, draft)
        self.add_item(TargetSelect(cog, draft))

    @discord.ui.button(label="提醒自己", style=discord.ButtonStyle.secondary, emoji="🐿️")
    async def remind_self(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.cog.finalize_draft(interaction, self.draft, None, None)


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
        self, interaction: discord.Interaction, message: str, once: str | None, at_time: str | None,
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
        repeat_choices = [every_hours, every_days, every_months]
        schedule_count = int(once is not None) + sum(value is not None for value in repeat_choices)
        if schedule_count == 0 and at_time is None:
            await interaction.response.send_message(text(language, "schedule_required"), ephemeral=True)
            return
        if schedule_count > 1 or (once is not None and at_time is not None):
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

        specified_run = self.parse_specific_time(at_time) if at_time is not None else None
        if at_time is not None and specified_run is None:
            await interaction.response.send_message(text(language, "invalid_specific_time"), ephemeral=True)
            return

        first_run_value: str | None = None
        if once is not None:
            duration = self.parse_once_duration(once)
            if duration is None:
                await interaction.response.send_message(text(language, "invalid_once_duration"), ephemeral=True)
                return
            schedule_key, schedule_amount = "once", self.duration_to_minutes(duration)
            schedule_value = text(language, "once_after", duration=duration)
            next_run = self.next_run(schedule_key, schedule_amount)
        elif every_hours is not None:
            schedule_key, schedule_amount = "every_hours", every_hours
            schedule_value = text(language, "every_hours", amount=every_hours)
            next_run = specified_run or self.next_run(schedule_key, schedule_amount)
            first_run_value = self.format_malaysia_time(specified_run, language) if specified_run else None
        elif every_days is not None:
            schedule_key, schedule_amount = "every_days", every_days
            schedule_value = text(language, "every_days", amount=every_days)
            next_run = specified_run or self.next_run(schedule_key, schedule_amount)
            first_run_value = self.format_malaysia_time(specified_run, language) if specified_run else None
        elif every_months is not None:
            schedule_key, schedule_amount = "every_months", every_months
            schedule_value = text(language, "every_months", amount=every_months)
            next_run = specified_run or self.next_run(schedule_key, schedule_amount)
            first_run_value = self.format_malaysia_time(specified_run, language) if specified_run else None
        else:
            # A specified time on its own is a one-time reminder.
            schedule_key, schedule_amount = "once", 0
            assert specified_run is not None
            next_run = specified_run
            schedule_value = text(language, "once_at", time=self.format_malaysia_time(specified_run, language))

        target_type = "member" if member is not None else "role" if role is not None else "member"
        target_id = member.id if member is not None else role.id if role is not None else interaction.user.id
        target = member.mention if member is not None else role.mention if role is not None else interaction.user.mention
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
        if first_run_value is not None:
            embed.add_field(name=text(language, "field_first_run"), value=first_run_value, inline=False)
        embed.set_footer(text=text(language, "scheduled_notice"))
        await interaction.response.send_message(embed=embed)

    async def show_channel_step(self, interaction: discord.Interaction, draft: ReminderDraft) -> None:
        """Move a guided reminder to its third, channel-selection step."""
        await interaction.response.send_message(
            ui_text(draft.language, "③ 選擇發佈頻道", "3. Choose posting channel"),
            view=ChannelView(self, draft),
            ephemeral=True,
        )

    async def resolve_post_channel(self, interaction: discord.Interaction, channel_id: int) -> discord.TextChannel | None:
        """Return a usable text channel selected from a Discord UI component."""
        guild = interaction.guild
        if guild is None:
            return None
        channel = guild.get_channel(channel_id)
        if channel is None:
            try:
                channel = await guild.fetch_channel(channel_id)
            except discord.HTTPException:
                return None
        if not isinstance(channel, discord.TextChannel):
            return None

        bot_user = self.bot.user
        me = guild.me or (guild.get_member(bot_user.id) if bot_user else None)
        if me is None and bot_user is not None:
            try:
                me = await guild.fetch_member(bot_user.id)
            except discord.HTTPException:
                return None
        if me is None:
            return None
        permissions = channel.permissions_for(me)
        if not permissions.view_channel or not permissions.send_messages:
            return None
        return channel

    async def finalize_draft(
        self,
        interaction: discord.Interaction,
        draft: ReminderDraft,
        member: discord.Member | None,
        role: discord.Role | None,
    ) -> None:
        """Validate the final two selections, persist the reminder, and confirm it."""
        assert draft.schedule_key is not None
        assert draft.schedule_amount is not None
        assert draft.next_run is not None
        destination = draft.post_channel
        if destination is None:
            await interaction.response.send_message(text(draft.language, "channel_unavailable"), ephemeral=True)
            return
        if role is not None and role.is_default() and not interaction.user.guild_permissions.mention_everyone:
            await interaction.response.send_message(text(draft.language, "everyone_denied"), ephemeral=True)
            return
        verified_destination = await self.resolve_post_channel(interaction, destination.id)
        if verified_destination is None:
            await interaction.response.send_message(text(draft.language, "channel_unavailable"), ephemeral=True)
            return
        destination = verified_destination

        target_type = "member" if member is not None else "role" if role is not None else "member"
        target_id = member.id if member is not None else role.id if role is not None else interaction.user.id
        target = member.mention if member is not None else role.mention if role is not None else interaction.user.mention
        self.connection.execute(
            """INSERT INTO reminders (guild_id, channel_id, creator_id, target_type, target_id, message,
               schedule_type, schedule_amount, next_run_at, language, creator_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                interaction.guild_id,
                destination.id,
                interaction.user.id,
                target_type,
                target_id,
                draft.message,
                draft.schedule_key,
                draft.schedule_amount,
                draft.next_run.isoformat(),
                draft.language,
                interaction.user.display_name,
            ),
        )
        self.connection.commit()

        embed = discord.Embed(title=text(draft.language, "scheduled_title"), colour=discord.Colour.teal())
        embed.add_field(name=text(draft.language, "field_message"), value=draft.message, inline=False)
        embed.add_field(name=text(draft.language, "field_type"), value=text(draft.language, f"type_{draft.schedule_key}"), inline=True)
        embed.add_field(name=text(draft.language, "field_interval"), value=draft.schedule_value or "—", inline=True)
        embed.add_field(name=text(draft.language, "field_target"), value=target, inline=True)
        embed.add_field(name=text(draft.language, "field_channel"), value=destination.mention, inline=True)
        if draft.first_run_value is not None:
            embed.add_field(name=text(draft.language, "field_first_run"), value=draft.first_run_value, inline=False)
        embed.set_footer(text=text(draft.language, "scheduled_notice"))
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
    def parse_specific_time(value: str, now: datetime | None = None) -> datetime | None:
        """Parse a Malaysia-local one-time time and return it in UTC.

        Supports ``今天 1730``, ``明天 1500``, and ``YYYYMMDD HHMM``.
        English clients may also enter ``today 1730`` or ``tomorrow 1500``.
        """
        match = SPECIFIC_TIME.fullmatch(value)
        if match is None:
            return None
        local_now = (now or datetime.now(MALAYSIA_TIMEZONE)).astimezone(MALAYSIA_TIMEZONE)
        date_value, time_value = match.group("date").lower(), match.group("time")
        hour, minute = int(time_value[:2]), int(time_value[2:])
        if hour > 23 or minute > 59:
            return None
        if date_value in {"today", "今天"}:
            target_date = local_now.date()
        elif date_value in {"tomorrow", "明天"}:
            target_date = (local_now + timedelta(days=1)).date()
        else:
            try:
                # The documented compact date is YYYYMMDD, matching the bot's
                # Chinese-first Malaysia-facing interface.
                target_date = datetime.strptime(date_value, "%Y%m%d").date()
            except ValueError:
                return None
        local_time = datetime(
            target_date.year, target_date.month, target_date.day, hour, minute, tzinfo=MALAYSIA_TIMEZONE
        )
        if local_time <= local_now:
            return None
        return local_time.astimezone(UTC)

    @staticmethod
    def format_malaysia_time(value: datetime, language: str) -> str:
        local_time = value.astimezone(MALAYSIA_TIMEZONE)
        if language == "zh":
            return f"{local_time.year}/{local_time.month:02d}/{local_time.day:02d} {local_time:%H:%M}（馬來西亞時間）"
        return f"{local_time:%Y/%m/%d %H:%M} (Malaysia time)"

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
    async def reminder(self, interaction: discord.Interaction) -> None:
        language = language_for(interaction.locale, self.bot.default_language)
        await interaction.response.send_modal(MessageModal(self, language))

    @app_commands.guild_only()
    @app_commands.command(name="提醒", description="建立並送出提醒。")
    async def reminder_chinese(self, interaction: discord.Interaction) -> None:
        language = language_for(interaction.locale, self.bot.default_language)
        await interaction.response.send_modal(MessageModal(self, language))

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
