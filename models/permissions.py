import discord
from tortoise.models import Model
from tortoise import fields
from typing import Any


class PermissionsOverride(Model):
    target_id = fields.IntField(primary_key=True, unique=True)
    target_type = fields.TextField(default="user")  # "user" or "role"

    command_id = fields.IntField()
    allowed = fields.BooleanField(default=True)

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    @classmethod
    async def check_for(cls, target: discord.Member | discord.Role, command: discord.ApplicationCommand) -> bool:
        override = await cls.get_or_none(target_id=target.id, command_id=command.id)

        if not override:
            return False

        return bool(override.allowed)

    @classmethod
    async def register_permission(
            cls, target: discord.Member | discord.Role, command: discord.ApplicationCommand,
            allowed: bool = True
    ):
        await cls.update_or_create(
            target_id=target.id, target_type="role" if type(target) is discord.Role else "user",
            command_id=command.id, allowed=allowed
        )


async def check_custom_permissions(ctx: discord.ApplicationContext) -> bool:
    """
    Checks if the user or one of his roles has custom permissions to use this command.
    :return:
    """

    result = await PermissionsOverride.check_for(ctx.author, ctx.command)
    if not result:
        return False

    return True
