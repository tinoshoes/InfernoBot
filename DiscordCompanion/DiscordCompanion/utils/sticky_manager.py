import discord
from discord.ext import commands
from typing import Dict, Optional

class StickyManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sticky_messages: Dict[int, Dict] = {}  # channel_id -> {message: str, last_message_id: Optional[int]}

    async def set_sticky_message(self, channel_id: int, message: str):
        """Set a sticky message for a channel"""
        self.sticky_messages[channel_id] = {
            "message": message,
            "last_message_id": None
        }

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Handle new messages in channels with sticky messages"""
        if message.author == self.bot.user:
            return

        channel_id = message.channel.id

        if channel_id not in self.sticky_messages:
            return

        sticky_data = self.sticky_messages[channel_id]

        # Delete the previous sticky message if it exists
        if sticky_data["last_message_id"]:
            try:
                old_message = await message.channel.fetch_message(sticky_data["last_message_id"])
                await old_message.delete()
            except (discord.NotFound, discord.Forbidden):
                pass

        # Send new sticky message
        new_sticky = await message.channel.send(sticky_data["message"])
        sticky_data["last_message_id"] = new_sticky.id

    async def remove_sticky_message(self, channel_id: int):
        """Remove sticky message from a channel"""
        if channel_id in self.sticky_messages:
            del self.sticky_messages[channel_id]

async def setup(bot):
    await bot.add_cog(StickyManager(bot))