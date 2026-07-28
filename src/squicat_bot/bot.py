"""Bot creation and command synchronisation."""

from __future__ import annotations

import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from squicat_bot.cogs.reminders import ReminderCog
from squicat_bot.i18n import language_for, text

LOGGER = logging.getLogger(__name__)


class SquicatBot(commands.Bot):
    """The application client for Squicat."""

    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.default_language = language_for(os.getenv("BOT_DEFAULT_LANGUAGE", "zh-TW"))
        raw_guild_id = os.getenv("DEV_GUILD_ID", "").strip()
        self.dev_guild_id = int(raw_guild_id) if raw_guild_id.isdigit() else None

    async def setup_hook(self) -> None:
        await self.add_cog(ReminderCog(self))
        if self.dev_guild_id:
            guild = discord.Object(id=self.dev_guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            LOGGER.info("Synced commands to development guild %s", self.dev_guild_id)
        else:
            await self.tree.sync()
            LOGGER.info("Synced global commands")

    async def on_ready(self) -> None:
        assert self.user is not None
        LOGGER.info("Logged in as %s (%s)", self.user, self.user.id)
        LOGGER.info(text(self.default_language, "ready"))


def run() -> None:
    """Load local settings and start the Discord client."""
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    token = os.getenv("DISCORD_TOKEN", "").strip()
    if not token or token == "replace_with_your_bot_token":
        raise RuntimeError("DISCORD_TOKEN is missing. Copy .env.example to .env and add your Bot Token.")
    SquicatBot().run(token, log_handler=None)
