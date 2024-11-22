from typing import Sequence

import discord
from discord import SlashCommandGroup
from discord.ext.commands import bot_has_permissions

from api import api_instance
from ctx import SubApplicationContext
from helpers import send_missing_custom_permissions_message, to_discord_emoji_name, emote_list_autocomplete, \
    ConfirmationView
from models import GuildSettings


class EmotesCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    command_group_7tv = SlashCommandGroup('7tv', description="7TV Related Commands")
    command_subgroup_7tv_emote = command_group_7tv.create_subgroup('emote', description="7TV Emote Commands")

    @command_subgroup_7tv_emote.command(
        name="add", description="Import a 7TV emote from a url. (Consider using emotes that weigh under 256kb)"
    )
    @bot_has_permissions(manage_emojis=True)
    async def emote_add(
            self, ctx: SubApplicationContext,
            emote_url: discord.Option(str, name='url', description='Direct 7TV Emote URL'),
            fit_to_square: discord.Option(
                bool, description="Makes the emote fit Square 1:1 Aspect Ratio",
            ),
            custom_name: discord.Option(
                str, description='Custom name for the emote (optional) [alphanumeric & _ only]', required=False,
                max_length=32, min_length=2
            ) = None,
            limit_to_role: discord.Option(
                discord.Role, name='role', description="Limit to specific role!",
            ) = None
    ):
        if not await ctx.guild_settings.check_custom_permissions(ctx):
            return await send_missing_custom_permissions_message(ctx)

        await ctx.defer(ephemeral=True)

        emote_id = emote_url.split("/")[-1]
        try:
            emote = await api_instance.emote_get(emote_id, fit_to_square)
        except Exception as e:
            await self.bot.on_application_command_error(ctx, e)  # type: ignore
            return

        uses_custom_name = True
        if not custom_name:
            custom_name = emote.name
            uses_custom_name = False

        custom_name = to_discord_emoji_name(custom_name)

        view = ConfirmationView()

        embed = discord.Embed(
            thumbnail=emote.emote_url,
            title=emote.name,
            description="**Are you sure you want to add this emote?**\n"
                        "*GIFs might have artifacts due to <a:7tv:1306003780898132112> being ass.*",
            color=discord.Color.embed_background()
        )

        embed.add_field(name='Custom Name', value=f"`{custom_name}`" if uses_custom_name else ":x:")
        embed.add_field(name='Fit to Square', value=":white_check_mark:" if fit_to_square else ":x:")

        if limit_to_role:
            embed.add_field(name='Limit To Role', value=limit_to_role.mention)

        message = await ctx.respond(embed=embed, view=view, ephemeral=True)

        await view.wait()

        if not view.value:
            view.disable_all_items()
            embed.description = "Cancelled."
            return await ctx.edit(embed=embed, view=view)

        discord_emote = await ctx.guild.create_custom_emoji(
            name=custom_name, image=emote.emote_bytes, roles=[limit_to_role] if limit_to_role else None,
            reason=f'{ctx.author.name} ({ctx.author.id}) imported a 7TV Emote "{emote.name}" [{emote.id}]'
        )
        await ctx.guild_settings.register_emote(ctx.author, emote, discord_emote.id)

        final_response = f":white_check_mark: Successfully created {discord_emote}"

        bot_user = ctx.guild.get_member(self.bot.user.id)
        if limit_to_role and limit_to_role not in bot_user.roles:
            final_response += (
                "\n:information_source: *If you don't see this emote, bot probably doesn't have "
                "the role you limited this emoji usage to!*"
            )

        embed.description = final_response
        embed.thumbnail = None
        embed.clear_fields()
        embed.title = None

        await message.delete()
        await ctx.send(content=ctx.author.mention, embed=embed)

    @command_subgroup_7tv_emote.command(
        name="remove", description="Remove a 7TV emote if it was added by you (or you are an admin)"
    )
    @bot_has_permissions(manage_emojis=True)
    async def remove_emote(
            self, ctx: SubApplicationContext,
            emote_id: discord.Option(
                str, name='emote', description='Name of the emote to delete.', autocomplete=emote_list_autocomplete
            )
    ):
        if not await ctx.guild_settings.check_custom_permissions(ctx):
            return await send_missing_custom_permissions_message(ctx)

        await ctx.defer(ephemeral=True)

        emote = await ctx.guild.fetch_emoji(int(emote_id))

        if ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_emojis:
            pass
        else:
            if emote.id not in await ctx.guild_settings.emotes_by(ctx.author):
                return await ctx.respond(f"{emote} wasn't added by you!", ephemeral=True)

        view = ConfirmationView()

        embed = discord.Embed(
            description=f"**Are you sure you want to remove {emote} ?**",
            color=discord.Color.red()
        )

        message = await ctx.respond(embed=embed, view=view, ephemeral=True)

        await view.wait()

        if not view.value:
            view.disable_all_items()
            embed.description = "Cancelled."
            return await ctx.edit(embed=embed, view=view)

        await ctx.guild_settings.remove_emote(emote.id)

        embed.description = f":x: **Removed emote `{emote.name}`** ({emote})"

        await message.delete()
        await ctx.send(content=ctx.author.mention, embed=embed)

        await ctx.guild.delete_emoji(
            emote, reason=f'{ctx.author.name} ({ctx.author.id}) removed a 7TV Emote "{emote.name}" [{emote.id}]'
        )

    @command_subgroup_7tv_emote.command(
        name="rename", description="Rename a 7TV emote if it was added by you (or you are an admin)"
    )
    @bot_has_permissions(manage_emojis=True)
    async def rename_emote(
            self, ctx: SubApplicationContext,
            emote_id: discord.Option(
                str, name='emote', description='Name of the emote to delete.', autocomplete=emote_list_autocomplete
            ),
            new_name: discord.Option(str, description="New name for the emote.", max_length=32, min_length=2)
    ):
        if not await ctx.guild_settings.check_custom_permissions(ctx):
            return await send_missing_custom_permissions_message(ctx)

        emote = await ctx.guild.fetch_emoji(int(emote_id))

        if ctx.author.guild_permissions.administrator or ctx.author.guild_permissions.manage_emojis:
            pass
        else:
            if emote.id not in await ctx.guild_settings.emotes_by(ctx.author):
                return await ctx.respond(f"{emote} wasn't added by you!", ephemeral=True)

        await ctx.defer()

        formatted_name = to_discord_emoji_name(new_name)

        await emote.edit(
            name=formatted_name,
            reason=f"Renamed from {emote.name} to {formatted_name} by {ctx.author.name} ({ctx.author.id})"
        )

        embed = discord.Embed(
            description=f":pencil2: Renamed emote {emote} to `{formatted_name}`",
            color=discord.Color.embed_background()
        )

        await ctx.respond(embed=embed, content=ctx.author.mention)

    @discord.Cog.listener()
    async def on_guild_emojis_update(
            self, guild: discord.Guild, before: Sequence[discord.Emoji], after: Sequence[discord.Emoji]
    ):
        removed_emotes: list[discord.Emoji] = list(set(before) - set(after))

        if len(removed_emotes) < 1:
            return

        guild_settngs, _ = await GuildSettings.get_or_create(guild_id=guild.id)

        for emote in removed_emotes:
            await guild_settngs.remove_emote(emote_id=emote.id)


def setup(bot: discord.Bot):
    bot.add_cog(EmotesCog(bot))
