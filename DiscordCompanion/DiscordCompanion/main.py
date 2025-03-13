import os
import discord
from discord.ext import commands
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('discord')

# Initialize bot with intents
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

# Create bot with help_command=None to disable default help
bot = commands.Bot(command_prefix='=', intents=intents, help_command=None)


@bot.event
async def on_ready():
    logger.info(f'{bot.user} has connected to Discord!')
    # Load cogs
    await bot.load_extension('cogs.admin_commands')
    await bot.load_extension('utils.sticky_manager')


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)


def main():
    token = os.getenv('MTM0NTUyMDI4MzY2NjM1MDIyMw.GOXFrQ.JyDUYcpd0cw2J3doZiWZs9TDBlXXFNKpmzPLOQ')
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable is required")

    bot.run(token)


if __name__ == "__main__":
    main()
