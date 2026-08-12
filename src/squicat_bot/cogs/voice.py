"""Owner-only, no-attribution posting commands."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from squicat_bot.i18n import language_for, text


class VoiceCog(commands.Cog):
    """Let only the Discord application owner post through Squicat."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _is_application_owner(self, user: discord.abc.User) -> bool:
        """Check the app owner, never a server-level administrator permission."""
        application = self.bot.application
        if application is None:
            application = await self.bot.application_info()
        return application.owner is not None and user.id == application.owner.id

    async def resolve_post_channel(
        self, interaction: discord.Interaction, channel_id: int
    ) -> discord.TextChannel | None:
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
        return channel if permissions.view_channel and permissions.send_messages else None

    async def _send_as_squicat(
        self,
        interaction: discord.Interaction,
        message: str,
        channel: discord.TextChannel,
    ) -> None:
        language = language_for(interaction.locale, self.bot.default_language)
        if not await self._is_application_owner(interaction.user):
            await interaction.response.send_message(
                text(language, "voice_owner_only"), ephemeral=True
            )
            return

        content = message.strip()
        if not content:
            await interaction.response.send_message(
                text(language, "voice_empty"), ephemeral=True
            )
            return

        destination = await self.resolve_post_channel(interaction, channel.id)
        if destination is None:
            await interaction.response.send_message(
                text(language, "channel_unavailable"), ephemeral=True
            )
            return

        try:
            # Keep the written text, but never send accidental member / role pings.
            await destination.send(
                content, allowed_mentions=discord.AllowedMentions.none()
            )
        except discord.HTTPException:
            await interaction.response.send_message(
                text(language, "voice_send_failed"), ephemeral=True
            )
            return

        await interaction.response.send_message(
            text(language, "voice_sent", channel=destination.mention), ephemeral=True
        )

    @app_commands.guild_only()
    @app_commands.command(
        name="say",
        description="Post a message as Squicat (application owner only).",
    )
    @app_commands.describe(message="Message Squicat should post", channel="Target channel")
    async def say(
        self,
        interaction: discord.Interaction,
        message: str,
        channel: discord.TextChannel,
    ) -> None:
        """Quick owner-only message posting in English."""
        await self._send_as_squicat(interaction, message, channel)

    @app_commands.guild_only()
    @app_commands.command(
        name="代發",
        description="讓松鼠小貓代為發送訊息（僅 Bot 擁有者）。",
    )
    @app_commands.rename(message="訊息", channel="頻道")
    @app_commands.describe(message="松鼠小貓要發出的內容", channel="選擇目標頻道")
    async def say_chinese(
        self,
        interaction: discord.Interaction,
        message: str,
        channel: discord.TextChannel,
    ) -> None:
        """Quick owner-only message posting in Traditional Chinese."""
        await self._send_as_squicat(interaction, message, channel)
