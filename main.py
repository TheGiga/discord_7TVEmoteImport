import os
import asyncio
import discord
import logging
import config
from discord import SlashCommandGroup
from tortoise import connections
from dotenv import load_dotenv
from discord.ext.commands import bot_has_permissions, has_permissions, MissingPermissions

load_dotenv()

from api import EmotesAPI
from api.errors import *
from database import db_init
from models import PermissionsOverride

logging.basicConfig(level=config.LOGGING_LEVEL)

intents = discord.Intents.default()
bot = discord.Bot(intents=intents)

api = EmotesAPI()

command_group_7tv = bot.create_group('7tv', description="7TV Related Commands")
command_subgroup_7tv_addemote = command_group_7tv.create_subgroup('addemote', description="7TV Emote Commands")

command_group_permissions = bot.create_group('permissions', description='Manage permissions for command usage.')


class ConfirmationView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(emoji="✔", style=discord.ButtonStyle.green)
    async def confirm_callback(self, b: discord.ui.Button, i: discord.Interaction):
        self.value = True
        self.stop()

    @discord.ui.button(emoji="❌", style=discord.ButtonStyle.grey)
    async def cancel_callback(self, b: discord.ui.Button, i: discord.Interaction):
        b.view.disable_all_items()
        await i.response.edit_message(content=".")

        self.value = False
        self.stop()


def qualified_commands_list() -> list[str]:
    available_commands: list[str] = []

    for cmd_object in bot.application_commands:
        if not isinstance(cmd_object, SlashCommandGroup):
            available_commands.append(cmd_object.qualified_name)
            continue

        cmd_object: SlashCommandGroup

        for inner_cmd_object in cmd_object.walk_commands():
            if isinstance(inner_cmd_object, SlashCommandGroup):
                continue

            available_commands.append(inner_cmd_object.qualified_name)

    return available_commands


async def commands_list_autocomplete(ctx: discord.AutocompleteContext):
    return [
        cmd for cmd in qualified_commands_list()
        if cmd not in config.IGNORED_COMMANDS_FOR_PERMISSIONS_OVERRIDES
        and cmd.startswith(ctx.value)
    ]


async def send_missing_custom_permissions_message(ctx: discord.ApplicationContext):
    try:
        await ctx.respond(
            content=":x: **You are not allowed to use this command!**\n"
                    "*Admins can use `/permissions set` to configure custom permissions.*",
            ephemeral=True
        )
    except discord.NotFound:
        await ctx.respond(
            content=":x: **You are not allowed to use this command!**\n"
                    "*Admins can use `/permissions set` to configure custom permissions.*",
        )
    except discord.HTTPException:
        pass


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
    print(type(error))

    if isinstance(error, MissingPermissions):
        return await send_error_response(
            ctx, error, f"Bot lacks permissions: `{error.missing_permissions}`"
        )

    elif isinstance(error, EmoteNotFound):
        return await send_error_response(
            ctx, error, f":x: **Emote Not Found!**"
        )

    elif isinstance(error, EmoteBytesReadFail):
        return await send_error_response(
            ctx, error, custom_message=
            f":x: Failed to read bytes for this emote\n*Report to administration if reoccurs.*"
        )

    elif isinstance(error, FailedToFindFittingEmote):
        return await send_error_response(
            ctx, error, custom_message=f":x: Failed to find fitting emote!\n"
                                       f"Most likely all the emote variants exceed Discord's file size limit: "
                                       f"`f{config.EMOJI_SIZE_LIMIT} bytes`"
        )

    elif isinstance(error, EmoteJSONReadFail):
        return await send_error_response(
            ctx, error, custom_message=":x: Failed to read JSON for this Emote, most likely Invalid URL!"
        )

    else:
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
    if command not in qualified_commands_list():
        return await ctx.respond(f":x: There is no such command! `/{command}`", ephemeral=True)

    await ctx.defer(ephemeral=True)

    await PermissionsOverride.register_permission(target=target, command=command, allowed=value)
    await ctx.respond(
        f"Successfully set {target.mention} permissions for `/{command}` to **`{value}`**.", ephemeral=True
    )


@command_subgroup_7tv_addemote.command(name="from_url")
@bot_has_permissions(manage_emojis=True)
async def addemote_from_url(
        ctx: discord.ApplicationContext,
        emote_url: discord.Option(name='url', description='Direct 7TV Emote URL'),
        custom_name: discord.Option(description='Custom name for the emote (optional)', required=False) = None,
        limit_to_role: discord.Option(discord.Role, name='role', description="Limit to specific role!") = None
):
    if not await PermissionsOverride.check_custom_permissions(ctx):
        return await send_missing_custom_permissions_message(ctx)

    await ctx.defer(ephemeral=True)

    emote_id = emote_url.split("/")[-1]
    try:
        content = await api.emote_get(emote_id)
    except Exception as e:
        await bot.on_application_command_error(ctx, e)  # type: ignore
        return

    if not custom_name:
        custom_name = content.name

    view = ConfirmationView()

    embed = discord.Embed(
        thumbnail=content.emote_url,
        description="Are you sure you want to add this emote?",
        color=discord.Color.embed_background()
    )

    message = await ctx.respond(embed=embed, view=view, ephemeral=True)

    await view.wait()

    if not view.value:
        view.disable_all_items()
        embed.description = "Cancelled."
        return await ctx.edit(embed=embed, view=view)

    emote = await ctx.guild.create_custom_emoji(
        name=custom_name, image=content.emote_bytes, roles=[limit_to_role] if limit_to_role else None
    )

    final_response = f":white_check_mark: Successfully created {emote}"

    bot_user = ctx.guild.get_member(bot.user.id)
    if limit_to_role and limit_to_role not in bot_user.roles:
        final_response += (
            "\n:information_source: *If you don't see this emote, bot probably doesn't have "
            "the role you limited this emoji usage to!*"
        )

    embed.description = final_response
    embed.thumbnail = None

    await message.delete()
    await ctx.respond(content=ctx.author.mention, embed=embed)


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
