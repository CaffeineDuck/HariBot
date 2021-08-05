"""
This is the main file for running the Bot
"""
import logging
import os

from .core import Bot
from .core.helpers import BotConfig
from .core.tortoise_config import tortoise_config
from .env import bot_config, db_config, lavalink_config

os.environ.setdefault("JISHAKU_HIDE", "1")
os.environ.setdefault("JISHAKU_RETAIN", "1")
os.environ.setdefault("JISHAKU_NO_UNDERSCORE", "1")

logging.basicConfig(level=logging.INFO)

cogs = ("bot.cogs.error_handler.error_handler",)

new_bot_config = BotConfig(
    prefix=bot_config.prefix,
    lavalink_config=lavalink_config,
    db_config=db_config,
    token=bot_config.token,
    log_webhook_url=bot_config.webhook_url,
    dev_env=bot_config.dev_env,
    cogs=cogs,
)


bot = Bot(config=new_bot_config, tortoise_config=tortoise_config)


if __name__ == "__main__":
    bot.run(new_bot_config.token)
