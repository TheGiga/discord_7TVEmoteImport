import discord
from discord import Interaction, Bot
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import GuildSettings


class SubApplicationContext(discord.ApplicationContext):
    def __init__(self, bot: Bot, interaction: Interaction):
        super().__init__(bot, interaction)
        self.guild_settings: GuildSettings = None
