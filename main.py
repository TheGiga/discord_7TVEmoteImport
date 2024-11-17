import os
import asyncio
import discord
import logging
from tortoise import connections
from dotenv import load_dotenv
from discord.ext.commands import MissingPermissions
load_dotenv()

import config
from api.errors import *
from database import db_init
from models import GuildSettings
from ctx import SubApplicationContext
from helpers import send_error_response
from bot import bot
from api import api_instance


logging.basicConfig(level=config.LOGGING_LEVEL)


@bot.check
async def overall_check(ctx: SubApplicationContext):
    if not ctx.bot.is_ready():
        await ctx.bot.wait_until_ready()

    # User creation if not present
    guild_settings, _ = await GuildSettings.get_or_create(guild_id=ctx.guild.id)

    ctx.guild_settings = guild_settings

    return True


@bot.event
async def on_application_command_error(ctx: SubApplicationContext, error):
    if isinstance(error, MissingPermissions):
        return await send_error_response(
            ctx, error, f"Bot lacks permissions: `{error.missing_permissions}`"
        )

    elif isinstance(error, EmoteNotFound):
        return await send_error_response(
            ctx, error, f":x: **Emote Not Found!**\nMake sure the URL you provided is correct!"
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


async def main():
    await api_instance.create_session()
    await db_init()
    await bot.start(os.getenv("TOKEN"))


if __name__ == "__main__":

    for cog in config.COGS:
        try:
            bot.load_extension(f'cogs.{cog}')
            print(f'Extension {cog} successfully loaded!')
        except discord.ExtensionNotFound:
            print(f'!!! Failed to load extension {cog}')

    event_loop = asyncio.get_event_loop_policy().get_event_loop()

    try:
        event_loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        print("🛑 Shutting Down")
        event_loop.run_until_complete(bot.close())
        event_loop.run_until_complete(connections.close_all(discard=True))
        event_loop.stop()
