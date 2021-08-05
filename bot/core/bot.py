"""This is the core for `Bot`"""

import asyncio
import traceback
from bot.utils.cog_manager import AutoReloader
import logging
from typing import Optional, Sequence

import discord
import wavelink
from aiohttp import ClientSession
from cachetools import TTLCache
from discord.ext import commands
from tortoise import Tortoise

from .help_command import HelpCommand
from .helpers.config import BotConfig, LavalinkConfig
from .models import GuildModel, UserModel


class Bot(commands.Bot):
    """This is the core `Bot`"""

    def __init__(self, config: BotConfig, tortoise_config: Optional[dict] = None):
        # Passes the args to the commands.Bot's init
        super().__init__(
            command_prefix=self._determine_prefix,
            description=config.description,
            help_command=HelpCommand(),
        )

        # lock_bot doesn't recieve message until its False
        self.lock_bot = True

        # Config object
        self.config = config
        self.tortoise_config = tortoise_config

        # Checks and connects to lavalink/DB according to config
        self._config_checker(self.config)

        # Cache Stuffs
        self._guild_model_cache = TTLCache(100, 1000)
        self._user_model_cache = TTLCache(100, 1000)

        # Wavelink Client
        self.wavelink_client = wavelink.Client(bot=self)

        # Loads cogs
        if self.config.load_jishaku:
            try:
                self.load_extension("jishaku")
            except commands.ExtensionAlreadyLoaded:
                pass

        # Logger
        self.logger = logging.getLogger("bot.main")

        # Auto Reloader
        if self.config.dev_env:
            autoreloader = AutoReloader(self)
            autoreloader.cog_watcher_task.start()

        # Cogs
        self._load_cogs()
            

    @property
    def event_loop(self) -> asyncio.BaseEventLoop:
        """
        This returns the existing event loop
        or creates a event loop and returns it
        """
        return asyncio.get_event_loop()

    @property
    def session(self) -> ClientSession:
        """
        This returns the aiohttp.ClientSession
        used by the discord.py
        """
        # pylint: disable=protected-access
        return self.http._HTTPClient__session

    @property
    def log_webhook(self) -> discord.Webhook:
        """
        This returns the discord.WebHook for
        logging info and errors
        """
        return discord.Webhook.from_url(
            self.config.log_webhook_url,
            adapter=discord.AsyncWebhookAdapter(self.session),
        )

    def _config_checker(self, config: BotConfig) -> None:
        """
        Checks config and handles the bot according to config
        """
        if config.db_config:
            # Locks the bot from handling on_message events
            self.lock_bot = True
            self.event_loop.create_task(self._connect_db(self.tortoise_config))

        if config.lavalink_config:
            self.event_loop.create_task(self._connect_wavelink(config.lavalink_config))

        if config.load_jishaku:
            self.load_extension("jishaku")

    async def _connect_db(self, tortoise_config: dict) -> None:
        """
        Connects to the postresql database
        """
        await self.wait_until_ready()

        if not tortoise_config:
            raise ValueError("Tortoise config must be passed")

        self.logger.info("Connecting to database")
        await Tortoise.init(tortoise_config)
        self.logger.info("Connected to database")
        self.lock_bot = False

    async def _connect_wavelink(self, lavalink_config: LavalinkConfig) -> None:
        """
        Connects to the wavelink nodes
        """
        await self.wait_until_ready()

        nodes = {
            lavalink_config.identifier: {
                "host": lavalink_config.host,
                "port": lavalink_config.port,
                "password": lavalink_config.password,
                "identifier": lavalink_config.identifier,
                "region": lavalink_config.region,
                "rest_uri": lavalink_config.rest_url,
            }
        }
        _ = [
            await self.wavelink_client.initiate_node(**node) for node in nodes.values()
        ]
        self.logger.info("Connected to wavelink nodes")

    async def _determine_prefix(
        self, bot: commands.Bot, message: discord.Message
    ) -> list[str]:
        """
        Get the prefix for each command invokation
        """
        if not message.guild:
            return [self.config.prefix]

        guild_model = await self.get_local_guild(message.guild.id)
        return commands.when_mentioned_or(guild_model.prefix)(bot, message)

    def _load_cogs(self) -> None:
        """
        Loads all the cogs from the config
        """
        if self.config.cogs:
            for cog in self.config.cogs:
                try:
                    self.load_extension(cog)
                    self.logger.info(f'Loaded Cog: {cog}')
                except commands.ExtensionError:
                    traceback.print_exc()

    # Working with cache
    async def get_local_guild(self, guild_id: int) -> GuildModel:
        """
        Get the Guild Model from the local database
        """
        guild_model = self._guild_model_cache.get(guild_id)

        if not guild_model:
            guild_model, _ = await GuildModel.get_or_create(id=guild_id)
            self._guild_model_cache[guild_id] = guild_model

        return guild_model

    async def update_local_guild(self, guild_model: GuildModel) -> None:
        """
        Updates the local Guild Models cache
        """
        self._guild_model_cache[guild_model.id] = guild_model

    async def get_local_user(self, user_id: int) -> None:
        """
        Get the User Model from the local database
        """
        user_model = self._user_model_cache.get(user_id)

        if not user_model:
            user_model, _ = await UserModel.get_or_create(id=user_id)

    async def update_local_user(self, user_model: UserModel) -> None:
        """
        Updates the local User Models cache
        """
        self._user_model_cache[user_model.id] = user_model

    # Event Listeners
    async def on_message(self, message: discord.Message) -> None:
        """
        Handles the `messages` for further processing
        """
        if self.lock_bot:
            return

        if f"<@!{self.user.id}>" == message.content.strip():
            prefixes = await self._determine_prefix(self, message)
            filtered_prefix = list(
                filter(
                    lambda x: not x.startswith("<@") and not x.endswith(">"), prefixes
                )
            )[0]
            return await message.reply(f"My prefix here is `{filtered_prefix}`")

        await self.process_commands(message)

    async def on_ready(self):
        """
        This method is executed when the bot is ready
        after startup
        """
        self.logger.info("Logged in with %s", self.user)
