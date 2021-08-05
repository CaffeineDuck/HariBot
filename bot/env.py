"""This modules parses environment variables"""

# pylint: disable=R0903, E0611

from typing import Optional

from pydantic import BaseSettings, HttpUrl

from .core.helpers.config import DatabaseConfig, LavalinkConfig

__all__ = ("bot_config", "db_config", "lavalink_config")


class BotConfig(BaseSettings):
    """
    Parses Bot config with environment variables
    """

    prefix: str
    token: str
    webhook_url: HttpUrl
    dev_env = False
    private_bot: Optional[bool]
    load_jishaku: Optional[bool]

    class Config:
        """This is the config class containg info about env prefix and file"""

        env_file = ".env"
        env_prefix = "bot_"


class BotDatabaseConfig(BaseSettings, DatabaseConfig):
    """
    Parses BoilerBot Database config with environment variables
    """

    class Config:
        """This is the config class containg info about env prefix and file"""

        env_file = ".env"
        env_prefix = "postgres_"


class BotLavalinkConfig(BaseSettings, LavalinkConfig):
    """
    Parses BoilerBot Database config with environment variables
    """

    class Config:
        """This is the config class containg info about env prefix and file"""

        env_file = ".env"
        env_prefix = "lavalink_"


bot_config = BotConfig()

db_config = BotDatabaseConfig()
# lavalink_config = BotLavalinkConfig()

# db_config = None
lavalink_config = None
