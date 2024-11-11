import discord
import config
from tortoise.models import Model
from tortoise import fields
from typing import Any

class PermissionsOverride(Model):
    command_name = fields.CharField(primary_key=True, unique=True, max_length=32)
    permissions = fields.JSONField(default=config.DEFAULT_PERMISSIONS_VALUE_JSON)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    @classmethod
    async def check_for(cls, target: discord.Member | discord.Role, command: discord.ApplicationCommand) -> bool:
        target_type: str = "roles" if type(target) is discord.Role else "user"
        target_discord_permissions: discord.Permissions = target.permissions if target_type == "role" else target.guild_permissions

        if not target_discord_permissions.administrator and config.IGNORE_OVERRIDES_IF_ADMINISTRATOR:
            return True

        override = await cls.get_or_none(command_name=command.qualified_name)

        if not override:
            return bool(config.DEFAULT_PERMISSIONS.get(command.qualified_name))

        target_list: list[int] = override.permissions[target_type]

        if target.id in target_list:
            return True

        return False

    @classmethod
    async def register_permission(
            cls, target: discord.Member | discord.Role, command: str,
            allowed: bool = True
    ):
        target_type: str = "roles" if type(target) is discord.Role else "user"
        override, _ = await cls.get_or_create(command_name=command)

        permissions_list: list[int] = override.permissions[target_type]

        if allowed:
            permissions_list.append(target.id)
        else:
            if target.id in override.permissions[target_type]:
                permissions_list.remove(target.id)

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
