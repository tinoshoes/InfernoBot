import discord
from discord.ext import commands

async def has_admin_permissions(ctx_or_interaction) -> bool:
    """
    Check if the user has administrator permissions
    Works with both Context and Interaction objects
    """
    if isinstance(ctx_or_interaction, discord.Interaction):
        if not ctx_or_interaction.guild:
            return False
        return (
            ctx_or_interaction.user.guild_permissions.administrator or
            ctx_or_interaction.user.guild_permissions.manage_guild
        )
    else:  # Commands Context
        if not ctx_or_interaction.guild:
            return False
        return (
            ctx_or_interaction.author.guild_permissions.administrator or
            ctx_or_interaction.author.guild_permissions.manage_guild
        )