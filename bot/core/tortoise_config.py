"""
This module contains `tortoise_config` Mapping which is used to
connect to database using Tortoise ORM
"""

from ..env import db_config

if not db_config:
    db_config = {}
else:
    tortoise_config = {
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "database": db_config.db,
                    "host": db_config.host,
                    "password": db_config.password,
                    "port": db_config.port,
                    "user": db_config.user,
                },
            }
        },
        "apps": {
            "main": {
                "models": ["bot.core.models", "aerich.models"],
                "default_connection": "default",
            }
        },
    }
