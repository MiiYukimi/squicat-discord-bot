"""Owner-only, no-attribution posting commands."""

from __future__ import annotations

from dataclasses import dataclass

import discord
from discord import app_commands
from discord.ext import commands

from squicat_bot.i18n import language_for, text


@dataclass
class VoiceDraft:
    """The short-lived content entered by the bot owner."""

    owner_id: int
    language: str
    message: str


class OwnerOnlyView(discord.ui.View):
    """Keep a posting flow private to the owner who started it."""

    def __init__(self, cog: "VoiceCog", draft: VoiceDraft) -> None:
        super().__init__(timeout=600)
        self.cog, self.draft = cog, draft

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == self.draft.owner_id:
            return True
        await interaction.response.send_message(text(self.draft.language, "voice_owner_only"), ephemeral=True)
        return False


class VoiceMessageModal(discord.ui.Modal):
    """First step: write the exact words the bot should say."""

    def __init__(self, cog: "VoiceCog", language: str) -> None:
        super().__init__(title=text(language, "voice_modal_title"))
        self.cog, self.language = cog, language
        self.message_input = discord.ui.TextInput(
            label=text(language, "voice_message_label"),
            placeholder=text(language, "voice_message_placeholder"),
            style=discord.TextStyle.paragraph,
            max_length=2_000,
        )
        self.add_item(self.message_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        message = self.message_input.value.strip()
        if not message:
            await interaction.response.send_message(text(self.language, "voice_empty"), ephemeral=True)
            return
        draft = VoiceDraft(interaction.user.id, self.language, message)
        await interaction.response.send_message(
            text(self.language, "voice_channel_step"),
            view=VoiceChannelView(self.cog, draft),
            ephemeral=True,
        )


class VoiceChannelSelect(discord.ui.ChannelSelect):
    """Second step: choose the channel in which the bot speaks."""

    def __init__(self, cog: "VoiceCog", draft: VoiceDraft) -> None:
        self.cog, self.draft = cog, draft
        super().__init__(
            placeholder=text(draft.language, "voice_channel_placeholder"),
            channel_types=[discord.ChannelType.text],
            min_values=1,
            max_values=1,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        channel = await self.cog.resolve_post_channel(interaction, self.values[0].id)
        if channel is None:
            await interaction.response.send_message(text(self.draft.language, "channel_unavailable"), ephemeral=True)
            return
        try:
            # Do not make @everyone, roles, or user mentions ping unexpectedly.
            # The text still displays exactly as written, but notifications stay off.
            await channel.send(self.draft.message, allowed_mentions=discord.AllowedMentions.none())
        except discord.HTTPException:
            await interaction.response.send_message(text(self.draft.language, "voice_send_failed"), ephemeral=True)
            return
        await interaction.response.edit_message(
            content=text(self.draft.language, "voice_sent", channel=channel.mention),
            view=None,
        )


class VoiceChannelView(OwnerOnlyView):
    def __init__(self, cog: "VoiceCog", draft: VoiceDraft) -> None:
        super().__init__(cog, draft)
        self.add_item(VoiceChannelSelect(cog, draft))


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

    async def _start_voice_flow(self, interaction: discord.Interaction) -> None:
        language = language_for(interaction.locale, self.bot.default_language)
        if not await self._is_application_owner(interaction.user):
            await interaction.response.send_message(text(language, "voice_owner_only"), ephemeral=True)
            return
        await interaction.response.send_modal(VoiceMessageModal(self, language))

    async def resolve_post_channel(self, interaction: discord.Interaction, channel_id: int) -> discord.TextChannel | None:
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

    @app_commands.guild_only()
    @app_commands.command(name="say", description="Post a message as Squicat (application owner only).")
    async def say(self, interaction: discord.Interaction) -> None:
        await self._start_voice_flow(interaction)

    @app_commands.guild_only()
    @app_commands.command(name="代發", description="讓松鼠小貓代為發送訊息（僅 Bot 擁有者）。")
    async def say_chinese(self, interaction: discord.Interaction) -> None:
        await self._start_voice_flow(interaction)
