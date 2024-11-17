import re
import discord
from discord import SlashCommandGroup

import config
from ctx import SubApplicationContext
from bot import bot


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


def to_discord_emoji_name(name) -> str:
    name = name.replace(" ", "_").replace("-", "_")
    name = re.sub(r"[^a-zA-Z0-9_]", "", name)

    return name if name else "emoji"


async def commands_list_autocomplete(ctx: discord.AutocompleteContext):
    return [
        cmd for cmd in qualified_commands_list()
        if cmd not in config.IGNORED_COMMANDS_FOR_PERMISSIONS_OVERRIDES
           and cmd.startswith(ctx.value)
    ]


async def emote_list_autocomplete(ctx: discord.AutocompleteContext):
    return [
        discord.OptionChoice(emote.name, str(emote.id)) for emote in ctx.interaction.guild.emojis
        if emote.name.lower().startswith(ctx.value.lower())
    ]


async def send_missing_custom_permissions_message(ctx: SubApplicationContext):
    try:
        await ctx.respond(
            content=":x: **You are not allowed to use this command!**\n"
                    "*Admins can use `/permissions allow` to configure custom permissions.*",
            ephemeral=True
        )
    except discord.NotFound:
        await ctx.respond(
            content=":x: **You are not allowed to use this command!**\n"
                    "*Admins can use `/permissions allow` to configure custom permissions.*",
        )
    except discord.HTTPException:
        pass


async def send_error_response(ctx, error, custom_message: str = None, ephemeral: bool = True):
    try:
        await ctx.respond(
            content=f":x: Unexpected error: ```{error}```" if not custom_message else custom_message,
            ephemeral=ephemeral
        )
    except discord.NotFound:
        await ctx.send(content=f":x: Unexpected error: ```{error}```" if not custom_message else custom_message)
    except discord.HTTPException:
        pass
