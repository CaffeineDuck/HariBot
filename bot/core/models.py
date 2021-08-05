"""This module contains the models for postgresql database"""

from tortoise import Model, fields

from ..env import bot_config


class GuildModel(Model):
    """
    `GuildModel` is used to store data about a guild in the database
    """

    id = fields.BigIntField(pk=True, description="Guild ID")
    prefix = fields.TextField(
        max_length=10,
        default=bot_config.prefix,
        description="Custom prefix of the guild",
    )

    # pylint: disable=R0903
    class Meta:
        """
        `GuildModel.Meta` is a meta class containg `GuildModel`
        database table;s info and description
        """

        table = "guilds"
        description = "Represent a discord guild"


class UserModel(Model):
    """
    `UserModel` is used to store data about a user in the database
    """

    id = fields.BigIntField(pk=True, description="User's ID")

    # pylint: disable=R0903
    class Meta:
        """
        `UserModel.Meta` is a meta class containg `UserModel`
        database table's info and description
        """

        table = "users"
        description = "Represent a discord user"
