"""Initial reminder Slash Commands for v0.1.0."""

from __future__ import annotations

import re

import discord
from discord import app_commands
from discord.ext import commands

from squicat_bot.i18n import language_for, text


ONCE_DURATION = re.compile(
    r"^\s*(?:(?P<hours>\d+)\s*h)?\s*(?:(?P<minutes>\d+)\s*m)?\s*$",
    re.IGNORECASE,
)


class ReminderCog(commands.Cog):
    """Validate reminder options before scheduling is introduced."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def create_preview(
        self,
        interaction: discord.Interaction,
        message: str,
        once: str | None,
        every_hours: int | None,
        every_days: int | None,
        every_months: int | None,
        member: discord.Member | None,
        role: discord.Role | None,
    ) -> None:
        language = language_for(interaction.locale, self.bot.default_language)
        target_count = int(member is not None) + int(role is not None)
        if target_count > 1:
            await interaction.response.send_message(text(language, "too_many_targets"), ephemeral=True)
            return
        if role is not None and role.is_default() and not interaction.user.guild_permissions.mention_everyone:
            await interaction.response.send_message(text(language, "everyone_denied"), ephemeral=True)
            return
        schedule_options = [once, every_hours, every_days, every_months]
        selected_count = sum(option is not None for option in schedule_options)
        if selected_count == 0:
            await interaction.response.send_message(text(language, "schedule_required"), ephemeral=True)
            return
        if selected_count > 1:
            await interaction.response.send_message(text(language, "only_one_schedule"), ephemeral=True)
            return

        if once is not None:
            duration = self.parse_once_duration(once)
            if duration is None:
                await interaction.response.send_message(text(language, "invalid_once_duration"), ephemeral=True)
                return
            schedule_key = "once"
            schedule_value = text(language, "once_after", duration=duration)
        elif every_hours is not None:
            schedule_key = "every_hours"
            schedule_value = text(language, "every_hours", amount=every_hours)
        elif every_days is not None:
            schedule_key = "every_days"
            schedule_value = text(language, "every_days", amount=every_days)
        else:
            schedule_key = "every_months"
            schedule_value = text(language, "every_months", amount=every_months)

        target = member.mention if member is not None else role.mention if role is not None else interaction.user.mention
        embed = discord.Embed(title=text(language, "preview_title"), colour=discord.Colour.teal())
        embed.add_field(name=text(language, "field_message"), value=message, inline=False)
        embed.add_field(name=text(language, "field_type"), value=text(language, f"type_{schedule_key}"), inline=True)
        embed.add_field(name=text(language, "field_interval"), value=schedule_value, inline=True)
        embed.add_field(name=text(language, "field_target"), value=target, inline=True)
        embed.set_footer(text=text(language, "preview_notice"))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @staticmethod
    def parse_once_duration(value: str) -> str | None:
        """Validate an h/m duration and return a clean display value."""
        match = ONCE_DURATION.fullmatch(value)
        if match is None or (match.group("hours") is None and match.group("minutes") is None):
            return None

        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        if hours == 0 and minutes == 0:
            return None
        return f"{hours}h{minutes}m" if hours and minutes else f"{hours}h" if hours else f"{minutes}m"

    @app_commands.guild_only()
    @app_commands.command(name="reminder", description="Create a reminder setup preview.")
    @app_commands.describe(
        message="What should Squicat remind them about?",
        once="Once only. Enter a duration such as 5h30m.",
        every_hours="Repeat every X hours. Enter X.",
        every_days="Repeat every X days. Enter X.",
        every_months="Repeat every X months. Enter X.",
        member="Optional. Leave blank to remind yourself; otherwise select one member.",
        role="Optional. Leave blank to remind yourself; otherwise select one role, including @everyone if permitted.",
    )
    async def reminder(
        self,
        interaction: discord.Interaction,
        message: app_commands.Range[str, 1, 1000],
        once: str | None = None,
        every_hours: app_commands.Range[int, 1, 8760] | None = None,
        every_days: app_commands.Range[int, 1, 8760] | None = None,
        every_months: app_commands.Range[int, 1, 8760] | None = None,
        member: discord.Member | None = None,
        role: discord.Role | None = None,
    ) -> None:
        await self.create_preview(interaction, message, once, every_hours, every_days, every_months, member, role)

    @app_commands.guild_only()
    @app_commands.command(name="提醒", description="建立提醒設定預覽。")
    @app_commands.rename(
        once="一次",
        every_hours="每x小時",
        every_days="每x天",
        every_months="每x個月",
    )
    @app_commands.describe(
        message="想提醒對方什麼？",
        once="一次提醒；填寫時間，例如 5h30m。",
        every_hours="每 X 小時提醒一次；直接填 X。",
        every_days="每 X 天提醒一次；直接填 X。",
        every_months="每 X 個月提醒一次；直接填 X。",
        member="選填；留空就提醒自己，否則選擇一位成員。",
        role="選填；留空就提醒自己，否則選擇一個身分組；有權限時可選 @everyone。",
    )
    async def reminder_chinese(
        self,
        interaction: discord.Interaction,
        message: app_commands.Range[str, 1, 1000],
        once: str | None = None,
        every_hours: app_commands.Range[int, 1, 8760] | None = None,
        every_days: app_commands.Range[int, 1, 8760] | None = None,
        every_months: app_commands.Range[int, 1, 8760] | None = None,
        member: discord.Member | None = None,
        role: discord.Role | None = None,
    ) -> None:
        await self.create_preview(interaction, message, once, every_hours, every_days, every_months, member, role)
