import discord
import config
from tortoise.models import Model
from tortoise import fields
from typing import Any


class PermissionsOverride(Model):
    #command_name = fields.CharField(primary_key=True, unique=True, max_length=32)
    guild_id = fields.IntField(primary_key=True, unique=True)
    permissions = fields.JSONField(default={})

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    @classmethod
    async def command_permissions(
            cls, guild: discord.Guild, command: str | discord.ApplicationCommand
    ) -> dict[str: list]:
        command_name = command if type(command) is str else command.qualified_name

        override, _ = await cls.get_or_create(guild_id=guild.id)

        if not override.permissions.get(command):
            return config.DEFAULT_PERMISSIONS_VALUE_JSON

        return override.permissions.get(command_name)

    @classmethod
    async def check_for(cls, target: discord.Member | discord.Role, command: str | discord.ApplicationCommand) -> bool:
        target_type: str = "role" if type(target) is discord.Role else "user"
        target_discord_permissions: discord.Permissions = \
            target.guild_permissions if target_type == "user" else target.permissions
        command_name = command if type(command) is str else command.qualified_name

        if not target_discord_permissions.administrator and config.IGNORE_OVERRIDES_IF_ADMINISTRATOR:
            return True

        override, _ = await cls.get_or_create(guild_id=target.guild.id)
        guild_permissions_list = override.permissions.get(command_name)

        if not guild_permissions_list:
            return bool(config.DEFAULT_PERMISSIONS.get(command_name))

        target_list: list[int] = guild_permissions_list[target_type]

        if target.id in target_list:
            return True

        return False

    @classmethod
    async def register_permission(
            cls, target: discord.Member | discord.Role, command: str,
            value: bool = True
    ):
        target_type: str = "role" if type(target) is discord.Role else "user"
        override, _ = await cls.get_or_create(guild_id=target.guild.id)

        if not override.permissions.get(command):
            override.permissions[command] = config.DEFAULT_PERMISSIONS_VALUE_JSON

        if value:
            if target.id not in override.permissions[command][target_type]:
                override.permissions[command][target_type].append(target.id)
        else:
            if target.id in override.permissions[command][target_type]:
                override.permissions[command][target_type].remove(target.id)

        await override.save()

    @staticmethod
    async def check_custom_permissions(ctx: discord.ApplicationContext) -> bool:
        """
        Checks if the user or one of his roles has custom permissions to use this command.
        :return:
        """
        if ctx.command.qualified_name in config.IGNORED_COMMANDS_FOR_PERMISSIONS_OVERRIDES:
            return True

        result = await PermissionsOverride.check_for(ctx.author, ctx.command)
        if not result:
            return False

        return True
