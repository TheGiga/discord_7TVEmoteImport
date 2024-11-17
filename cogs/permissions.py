import discord
from discord import SlashCommandGroup
from discord.ext.commands import has_permissions
from ctx import SubApplicationContext
from helpers import commands_list_autocomplete, qualified_commands_list


class PermissionsCog(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    command_group_permissions = SlashCommandGroup('permissions', description='Manage permissions for command usage.')

    @command_group_permissions.command(
        name="allow", description="Enable access for a user/role to a specific command."
    )
    @has_permissions(administrator=True)
    async def permissions_allow(
            self, ctx: SubApplicationContext,
            target: discord.Option(discord.abc.Mentionable, description="Allow Role or User to use the command."),
            command: discord.Option(
                description="Command to set permissions for. (uses qualified command name, f.e `permissions allow`)",
                autocomplete=commands_list_autocomplete
            )
    ):
        if command not in qualified_commands_list():
            return await ctx.respond(f":x: There is no such command! `/{command}`", ephemeral=True)

        await ctx.defer(ephemeral=True)

        await ctx.guild_settings.register_permission(target=target, command=command, value=True)
        await ctx.respond(
            f"**Successfully allowed {target.mention} to use `/{command}`**.", ephemeral=True
        )

    @command_group_permissions.command(
        name="remove", description="Remove custom permissions for a user/role to a specific command."
    )
    @has_permissions(administrator=True)
    async def permissions_remove(
            self, ctx: SubApplicationContext,
            target: discord.Option(discord.abc.Mentionable, description="Allow Role or User to use the command."),
            command: discord.Option(
                description="Command to set permissions for. (uses qualified command name, f.e `permissions allow`)",
                autocomplete=commands_list_autocomplete
            )
    ):
        if command not in qualified_commands_list():
            return await ctx.respond(f":x: There is no such command! `/{command}`", ephemeral=True)

        await ctx.defer(ephemeral=True)

        await ctx.guild_settings.register_permission(target=target, command=command, value=False)
        await ctx.respond(
            f"**Successfully removed permissions to use `/{command}` for {target.mention}**.", ephemeral=True
        )

    @command_group_permissions.command(name="list", description="Get the list of all custom permissions ")
    async def permissions_list(
            self, ctx: SubApplicationContext,
            command: discord.Option(
                description="Command to set permissions for. (uses qualified command name, f.e `permissions set`)",
                autocomplete=commands_list_autocomplete
            )
    ):
        if command not in qualified_commands_list():
            return await ctx.respond(f":x: There is no such command! `/{command}`", ephemeral=True)

        overrides = await ctx.guild_settings.get_command_permissions(command)

        if len(overrides["role"]) + len(overrides["user"]) < 1:
            await ctx.respond(f"There are no custom permissions for command `/{command}`", ephemeral=True)
            return

        embed = discord.Embed(title=f"Custom permissions for `/{command}`", color=discord.Color.embed_background())
        embed.description = "*If role/user is in the list - it has permissions to use the command.*"

        if len(overrides["role"]) > 0:
            value = " ".join(f"<@&{item}>" for item in overrides["role"])

            embed.add_field(name=f'Roles: ({len(overrides["role"])})', value=value)

        if len(overrides["user"]) > 0:
            value = " ".join(f"<@{item}>" for item in overrides["user"])

            embed.add_field(name=f'Users: ({len(overrides["user"])})', value=value)

        await ctx.respond(embed=embed)


def setup(bot: discord.Bot):
    bot.add_cog(PermissionsCog(bot))
