"""Initial reminder Slash Commands for v0.1.0."""

from __future__ import annotations

from enum import Enum

import discord
from discord import app_commands
from discord.ext import commands

from squicat_bot.i18n import language_for, text


class ReminderType(str, Enum):
    ONCE = "once"
    IN_MINUTES = "in_minutes"
    IN_HOURS = "in_hours"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    EVERY_HOURS = "every_hours"


class ReminderCog(commands.Cog):
    """Validate reminder options before scheduling is introduced."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def create_preview(
        self,
        interaction: discord.Interaction,
        message: str,
        reminder_type: ReminderType,
        member: discord.Member | None,
        role: discord.Role | None,
        amount: app_commands.Range[int, 1, 8760] | None,
    ) -> None:
        language = language_for(interaction.locale, self.bot.default_language)
        target_count = int(member is not None) + int(role is not None)
        if target_count == 0:
            await interaction.response.send_message(text(language, "missing_target"), ephemeral=True)
            return
        if target_count > 1:
            await interaction.response.send_message(text(language, "too_many_targets"), ephemeral=True)
            return
        if role is not None and role.is_default() and not interaction.user.guild_permissions.mention_everyone:
            await interaction.response.send_message(text(language, "everyone_denied"), ephemeral=True)
            return
        timed_types = {ReminderType.IN_MINUTES, ReminderType.IN_HOURS, ReminderType.EVERY_HOURS}
        if reminder_type in timed_types and amount is None:
            await interaction.response.send_message(text(language, "amount_required"), ephemeral=True)
            return
        if reminder_type not in timed_types and amount is not None:
            await interaction.response.send_message(text(language, "amount_not_needed"), ephemeral=True)
            return

        type_key = f"type_{reminder_type.value}"
        target = member.mention if member is not None else role.mention  # type: ignore[union-attr]
        embed = discord.Embed(title=text(language, "preview_title"), colour=discord.Colour.teal())
        embed.add_field(name=text(language, "field_message"), value=message, inline=False)
        embed.add_field(name=text(language, "field_type"), value=text(language, type_key), inline=True)
        embed.add_field(name=text(language, "field_target"), value=target, inline=True)
        if amount is not None:
            interval_key = {
                ReminderType.IN_MINUTES: "in_minutes",
                ReminderType.IN_HOURS: "in_hours",
                ReminderType.EVERY_HOURS: "every_hours",
            }[reminder_type]
            embed.add_field(name=text(language, "field_interval"), value=text(language, interval_key, amount=amount), inline=True)
        embed.set_footer(text=text(language, "preview_notice"))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.guild_only()
    @app_commands.command(name="reminder", description="Create a reminder setup preview.")
    @app_commands.describe(
        message="What should Squicat remind them about?",
        reminder_type="How often should the reminder repeat?",
        member="One member to remind.",
        role="One role to remind, including @everyone if permitted.",
        amount="Required for in X minutes, in X hours, or every X hours.",
    )
    @app_commands.choices(
        reminder_type=[
            app_commands.Choice(name="Once", value=ReminderType.ONCE.value),
            app_commands.Choice(name="In X minutes (once)", value=ReminderType.IN_MINUTES.value),
            app_commands.Choice(name="In X hours (once)", value=ReminderType.IN_HOURS.value),
            app_commands.Choice(name="Daily", value=ReminderType.DAILY.value),
            app_commands.Choice(name="Weekly", value=ReminderType.WEEKLY.value),
            app_commands.Choice(name="Monthly", value=ReminderType.MONTHLY.value),
            app_commands.Choice(name="Every X hours", value=ReminderType.EVERY_HOURS.value),
        ]
    )
    async def reminder(
        self,
        interaction: discord.Interaction,
        message: app_commands.Range[str, 1, 1000],
        reminder_type: app_commands.Choice[str],
        member: discord.Member | None = None,
        role: discord.Role | None = None,
        amount: app_commands.Range[int, 1, 8760] | None = None,
    ) -> None:
        await self.create_preview(interaction, message, ReminderType(reminder_type.value), member, role, amount)

    @app_commands.guild_only()
    @app_commands.command(name="提醒", description="建立提醒設定預覽。")
    @app_commands.describe(
        message="想提醒對方什麼？",
        reminder_type="提醒要如何重複？",
        member="一位要提醒的成員。",
        role="一個要提醒的身分組；有權限時可選 @everyone。",
        amount="「X 分鐘後」、「X 小時後」或「每 X 小時」才需要填寫。",
    )
    @app_commands.choices(
        reminder_type=[
            app_commands.Choice(name="一次", value=ReminderType.ONCE.value),
            app_commands.Choice(name="X 分鐘後（一次）", value=ReminderType.IN_MINUTES.value),
            app_commands.Choice(name="X 小時後（一次）", value=ReminderType.IN_HOURS.value),
            app_commands.Choice(name="每天", value=ReminderType.DAILY.value),
            app_commands.Choice(name="每星期", value=ReminderType.WEEKLY.value),
            app_commands.Choice(name="每月", value=ReminderType.MONTHLY.value),
            app_commands.Choice(name="每 X 小時", value=ReminderType.EVERY_HOURS.value),
        ]
    )
    async def reminder_chinese(
        self,
        interaction: discord.Interaction,
        message: app_commands.Range[str, 1, 1000],
        reminder_type: app_commands.Choice[str],
        member: discord.Member | None = None,
        role: discord.Role | None = None,
        amount: app_commands.Range[int, 1, 8760] | None = None,
    ) -> None:
        await self.create_preview(interaction, message, ReminderType(reminder_type.value), member, role, amount)
