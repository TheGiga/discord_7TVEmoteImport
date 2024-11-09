import os
import asyncio
import discord
import logging

from discord import SlashCommandGroup
from tortoise import connections

import config
from dotenv import load_dotenv
from discord.ext.commands import bot_has_permissions, has_permissions

load_dotenv()

from api import EmotesAPI
from api.errors import *
from database import db_init
from errors import MissingCustomPermissions
from models.permissions import check_custom_permissions

logging.basicConfig(level=config.LOGGING_LEVEL)

intents = discord.Intents.default()
bot = discord.Bot(intents=intents)

api = EmotesAPI()

command_group_7tv = bot.create_group('7tv', description="7TV Related Commands")
command_subgroup_7tv_addemote = command_group_7tv.create_subgroup('addemote', description="7TV Emote Commands")

command_group_permissions = bot.create_group('permissions', description='Manage permissions for command usage.')


async def commands_list_autocomplete(ctx: discord.AutocompleteContext):
    available_commands: list[str] = []

    for cmd_object in bot.application_commands:
        if not isinstance(cmd_object, SlashCommandGroup):
            if cmd_object.qualified_name.startswith(ctx.value):
                available_commands.append(cmd_object.qualified_name)
                continue

        cmd_object: SlashCommandGroup

        for inner_cmd_object in cmd_object.walk_commands():
            if isinstance(inner_cmd_object, SlashCommandGroup):
                continue

            available_commands.append(inner_cmd_object.qualified_name)

    return available_commands


async def send_error_response(ctx, error, custom_message: str = None, ephemeral: bool = False):
    try:
        await ctx.respond(
            content=f":x: Unexpected error: ```{error}```" if not custom_message else custom_message,
            ephemeral=ephemeral
        )
    except discord.NotFound:
        await ctx.send(content=f":x: Unexpected error: ```{error}```" if not custom_message else custom_message)
    except discord.HTTPException:
        pass


@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    if isinstance(error, discord.ext.commands.MissingPermissions):
        return await send_error_response(
            ctx, error, f"Bot lacks permissions: `{error.missing_permissions}`"
        )

    if isinstance(error, EmoteNotFound):
        return await send_error_response(
            ctx, error, f":x: **Emote Not Found!**"
        )

    if isinstance(error, EmoteBytesReadFail):
        return await send_error_response(
            ctx, error, custom_message=
            f":x: Failed to read bytes for this emote\n*Report to administration if reoccurs.*"
        )

    if isinstance(error, FailedToFindFittingEmote):
        return await send_error_response(
            ctx, error, custom_message=f":x: Failed to find fitting emote!\n"
                                       f"Most likely all the emote variants exceed Discord's file size limit: "
                                       f"`f{config.EMOJI_SIZE_LIMIT} bytes`"
        )

    if isinstance(error, EmoteJSONReadFail):
        return await send_error_response(
            ctx, error, custom_message=":x: Failed to read JSON for this Emote, most likely Invalid URL!"
        )

    if isinstance(error, MissingCustomPermissions):
        return await send_error_response(
            ctx, error, custom_message=":x: **You are not allowed to use this command!**",
            ephemeral=True
        )

    await send_error_response(ctx, error)
    raise error


@command_group_permissions.command(name="set")
@has_permissions(administrator=True)
async def permissions_set(
        ctx: discord.ApplicationContext,
        target: discord.Option(discord.abc.Mentionable, description="Role or User to set permissions for."),
        command: discord.Option(
            description="Command to set permissions for. (uses qualified command name, f.e `permissions set`)",
            autocomplete=commands_list_autocomplete
        ),
        value: discord.Option(bool)
):
    print(command.value)

    #if command not in [cmd.id for cmd in bot.commands]:
        #return await ctx.respond(f":x: There is no such command!", ephemeral=True)

    await ctx.defer()

    await ctx.respond(f"{target=}, {command=}, {value=}")


@command_subgroup_7tv_addemote.command(name="from_url")
@bot_has_permissions(manage_emojis=True)
async def addemote_from_url(
        ctx: discord.ApplicationContext,
        emote_url: discord.Option(name='url', description='Direct 7TV Emote URL'),
        custom_name: discord.Option(description='Custom name for the emote (optional)', required=False) = None,
        limit_to_role: discord.Option(discord.Role, name='role', description="Limit to specific role!") = None
):
    has_perms = await check_custom_permissions(ctx)

    if not has_perms:
        raise MissingCustomPermissions

    await ctx.defer()

    emote_id = emote_url.split("/")[-1]
    try:
        content = await api.emote_get(emote_id)
    except Exception as e:
        await bot.on_application_command_error(ctx, e)  # type: ignore
        return

    if not custom_name:
        custom_name = content.name

    emote = await ctx.guild.create_custom_emoji(name=custom_name, image=content.emote_bytes, roles=[limit_to_role])

    response = f":white_check_mark: Successfully created {emote}"

    bot_member = ctx.guild.get_member(bot.user.id)
    if limit_to_role and limit_to_role not in bot_member.roles:
        response += (
            "\n:information_source: *If you don't see this emote, bot probably doesn't have "
            "the role you limited this emoji usage to!*"
        )

    await ctx.respond(response)


async def main():
    await api.create_session()
    await db_init()
    await bot.start(os.getenv("TOKEN"))


if __name__ == "__main__":

    event_loop = asyncio.get_event_loop_policy().get_event_loop()
    api = EmotesAPI()

    try:
        event_loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        print("🛑 Shutting Down")
        event_loop.run_until_complete(bot.close())
        event_loop.run_until_complete(connections.close_all(discard=True))
        event_loop.stop()
