import discord
import config
from tortoise.models import Model
from tortoise import fields
from typing import Any
from api import Emote
from ctx import SubApplicationContext


class DuplicateEmoteIDRecord(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class GuildSettings(Model):
    guild_id = fields.IntField(primary_key=True, unique=True)
    permissions = fields.JSONField(default={})
    emotes = fields.JSONField(default={})

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    @staticmethod
    async def check_custom_permissions(ctx: SubApplicationContext) -> bool:
        """
        Checks if the user or one of his roles has custom permissions to use this command.
        :return:
        """
        if ctx.command.qualified_name in config.IGNORED_COMMANDS_FOR_PERMISSIONS_OVERRIDES:
            return True

        result = await ctx.guild_settings.check_permissions_for(ctx.author, ctx.command)
        if not result:
            return False

        return True

    async def get_command_permissions(
            self, command: str | discord.ApplicationCommand
    ) -> dict[str: list]:
        command_name = command if type(command) is str else command.qualified_name

        return self.permissions.get(command_name, config.DEFAULT_PERMISSIONS_VALUE_JSON)

    async def check_permissions_for(
            self, target: discord.Member | discord.Role, command: str | discord.ApplicationCommand
    ) -> bool:
        target_type: str = "role" if type(target) is discord.Role else "user"
        target_discord_permissions: discord.Permissions = \
            target.guild_permissions if target_type == "user" else target.permissions
        command_name = command if type(command) is str else command.qualified_name

        if target_discord_permissions.administrator and config.IGNORE_OVERRIDES_IF_ADMINISTRATOR:
            return True

        guild_permissions_list = self.permissions.get(command_name)

        if not guild_permissions_list:
            return bool(config.DEFAULT_PERMISSIONS.get(command_name))

        target_list_role: list[int] = guild_permissions_list["role"]
        target_list_user: list[int] = guild_permissions_list["user"]

        if target.id in target_list_user:
            return True

        if type(target) is discord.Member:
            if any(item.id in target_list_role for item in target.roles):
                return True

        return False

    async def register_permission(
            self, target: discord.Member | discord.Role, command: str,
            value: bool = True
    ):
        target_type: str = "role" if type(target) is discord.Role else "user"

        if not self.permissions.get(command):
            self.permissions[command] = config.DEFAULT_PERMISSIONS_VALUE_JSON

        if value:
            if target.id not in self.permissions[command][target_type]:
                self.permissions[command][target_type].append(target.id)
        else:
            if target.id in self.permissions[command][target_type]:
                self.permissions[command][target_type].remove(target.id)

        await self.save()

    async def register_emote(self, author: discord.Member, emote: Emote, discord_emote_id: int):
        if not self.emotes.get(discord_emote_id):
            self.emotes[discord_emote_id] = {
                "seventv_id": emote.id,
                "discord_id": discord_emote_id,
                "author_id": author.id,
                "animated": emote.animated
            }

            await self.save()
            return

        raise DuplicateEmoteIDRecord(f"Tried to create a DB record with duplicate discord emote ID: {discord_emote_id}")

    async def emotes_by(self, target: discord.Member) -> list[int]:
        return [
            int(emote_key) for emote_key in self.emotes
            if self.emotes[emote_key]["author_id"] == target.id
        ]

    async def get_emote_by_discord_id(self, emote_id: int) -> dict | None:
        return self.emotes.get(str(emote_id), None)

    async def remove_emote(self, emote_id: int):
        popped = self.emotes.pop(str(emote_id), None)

        if popped:
            await self.save()

    @classmethod
    async def unregister_deleted_emotes(cls, guild: discord.Guild):
        guild_settings, created = await cls.get_or_create(guild_id=guild.id)

        if created:
            return

        registered_emotes = [emote_key for emote_key in guild_settings.emotes]
        guild_emotes = [str(x.id) for x in await guild.fetch_emojis()]

        for emote in registered_emotes:
            if emote in guild_emotes:
                continue

            guild_settings.emotes.pop(emote)

        await guild_settings.save()
