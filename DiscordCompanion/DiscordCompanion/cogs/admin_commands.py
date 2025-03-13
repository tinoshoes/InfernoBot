import discord
from discord.ext import commands
from utils.permissions import has_admin_permissions
from datetime import datetime, timedelta
import random


class AdminCommands(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.spam_active = {
        }  # user_id -> bool tracking active spam operations
        self.spam_cap = 100  # Default spam cap
        self.warnings = {}  # user_id -> list of {reason, timestamp, warner_id}
        self.locked_servers = {
        }  # guild_id -> bool tracking which servers have locking enabled
        self.afk_users = {
        }  # user_id -> {"nickname": original_nickname, "reason": reason}
        self.ping_responses = [
            "hi", "what's up?", "yo", "fuck off", "leave me alone",
            "who pinged me?", "what do you want?", "can't you see I'm busy?",
            "bruh", "*sigh* what now?"
        ]

    @commands.command(name="dm")
    async def dm(self, ctx: commands.Context, user: discord.Member, *,
                 message: str):
        """Send a direct message to a user"""
        try:
            await user.send(message)
            await ctx.send(f"✅ DM sent to {user.mention}")
        except discord.Forbidden:
            await ctx.send(f"I don't have permission to DM {user.mention}")
        except Exception as e:
            await ctx.send(f"Failed to send DM: {str(e)}")

    @commands.command(name="check")
    async def check(self, ctx: commands.Context):
        """Respond with a status message"""
        await ctx.send("I'm well and alive!")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages from the bot itself
        if message.author == self.bot.user:
            return

        # Remove AFK if user types
        if message.author.id in self.afk_users:
            try:
                # Restore original nickname
                original_nick = self.afk_users[message.author.id]["nickname"]
                await message.author.edit(nick=original_nick)
                del self.afk_users[message.author.id]

                embed = discord.Embed(
                    description=f"Welcome back {message.author.mention}!",
                    color=discord.Color.blue())
                await message.channel.send(embed=embed)
            except discord.Forbidden:
                pass  # Ignore permission errors for nickname changes
            except Exception:
                pass  # Ignore any other errors during auto-removal

        # Check for bot mention
        if self.bot.user in message.mentions:
            response = random.choice(self.ping_responses)
            await message.reply(response)

        # Check for AFK user mentions
        for mentioned in message.mentions:
            if mentioned.id in self.afk_users:
                afk_data = self.afk_users[mentioned.id]
                reason = afk_data["reason"]
                await message.reply(
                    f"{mentioned.display_name} is AFK: {reason}")

        # Convert message to lowercase for case-insensitive matching
        content = message.content.lower()
        trigger_words = ["rat", "ratted", "virus"]

        # Split the message into words and check if any exact trigger word is in the message
        words = content.split()
        if any(word in words for word in trigger_words):
            response = (
                "# The paid menu is not ratted! We spend so much time developing this menu, "
                "if it was ratted it would be easily debunked and ruin our reputation. "
                "The large file is mainly because of obfusucation and we can assure you, "
                "the menu is not ratted. Additionally, this menu is created by trusted devs "
                "who have experience in modding and coding. The dev \".infxrno.\" coded me! #\n\n"
                "- Delivered From Azure Modding")

            # Create an embed for a cleaner DM
            embed = discord.Embed(description=response,
                                  color=discord.Color.blue())

            try:
                await message.author.send(embed=embed)
                # Add a subtle reaction to indicate the DM was sent
                await message.add_reaction("✉️")
            except discord.Forbidden:
                # If we can't DM the user, send it as a regular reply with the same embed
                await message.reply(embed=embed)

        # Only check for role if server is locked
        if message.guild and self.locked_servers.get(message.guild.id, False):
            blocked_roles = [
                1339078554901545001,  # Original role
                1345027173039341618,  # New role 1
                1339029494228324413  # New role 2
            ]
            if any(role.id in blocked_roles for role in message.author.roles):
                try:
                    await message.delete()
                except discord.Forbidden:
                    pass  # Bot doesn't have permission to delete messages
                except discord.NotFound:
                    pass  # Message was already deleted

    @commands.command(name="setspam")
    async def setspam(self, ctx: commands.Context, new_cap: int):
        """Set a new spam message limit"""
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        if new_cap < 1:
            await ctx.send("Spam cap must be at least 1 message!")
            return

        self.spam_cap = new_cap
        await ctx.send(
            f"✅ Spam message limit has been set to {new_cap} messages.")

    @commands.command(name="info")
    async def info(self, ctx: commands.Context):
        """Display information about Azure Modding"""
        info_message = (
            "Azure Modding was founded not too long ago with the sole intent to mod the popular game Gorilla Tag. "
            "The Developers Of The Azure Menu are: Inferno, Tagmonke, Dave Ghroul, and last but not least, Sudzythegoat."
        )
        await ctx.send(info_message)

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        """Get the bot's current websocket latency"""
        latency = round(self.bot.latency * 1000)  # Convert to milliseconds
        await ctx.send(f"Pong! `{latency}ms`")

    @commands.command(name="lock")
    async def lock(self, ctx: commands.Context):
        """Toggle message blocking for users with the muted role"""
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        guild_id = ctx.guild.id

        # Enable locking
        self.locked_servers[guild_id] = True
        await ctx.send(
            "🔒 Role message blocking has been enabled. Messages from users with the specified role will be deleted."
        )

    @commands.command(name="unlock")
    async def unlock(self, ctx: commands.Context):
        """Disable message blocking for users with the muted role"""
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        guild_id = ctx.guild.id

        # Disable locking by removing the guild from locked servers
        if guild_id in self.locked_servers:
            del self.locked_servers[guild_id]
            await ctx.send("🔓 Role message blocking has been disabled.")
        else:
            await ctx.send("Role message blocking is already disabled.")

    @commands.command(name="ban")
    async def ban(self,
                  ctx: commands.Context,
                  user: discord.Member,
                  delete_days: int = 0,
                  *,
                  reason: str = "No reason provided"):
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        try:
            await user.ban(reason=reason, delete_message_days=delete_days)
            await ctx.send(
                f"✅ Successfully banned {user.mention}\nReason: {reason}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to ban this user!")
        except Exception as e:
            await ctx.send(f"Failed to ban user: {str(e)}")

    @commands.command(name="kick")
    async def kick(self,
                   ctx: commands.Context,
                   user: discord.Member,
                   *,
                   reason: str = "No reason provided"):
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        try:
            await user.kick(reason=reason)
            await ctx.send(
                f"✅ Successfully kicked {user.mention}\nReason: {reason}")
        except discord.Forbidden:
            await ctx.send("I don't have permission to kick this user!")
        except Exception as e:
            await ctx.send(f"Failed to kick user: {str(e)}")

    @commands.command(name="mute")
    async def mute(self,
                   ctx: commands.Context,
                   user: discord.Member,
                   duration: int,
                   *,
                   reason: str = "No reason provided"):
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        try:
            # Calculate unmute time
            unmute_time = datetime.utcnow() + timedelta(minutes=duration)

            # Timeout the user
            await user.timeout(unmute_time, reason=reason)

            await ctx.send(
                f"✅ Successfully muted {user.mention} for {duration} minutes\nReason: {reason}"
            )
        except discord.Forbidden:
            await ctx.send("I don't have permission to mute this user!")
        except Exception as e:
            await ctx.send(f"Failed to mute user: {str(e)}")

    @commands.command(name="sticky")
    async def sticky(self, ctx: commands.Context, *, message: str):
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        try:
            # Get the sticky manager from the bot
            sticky_manager = self.bot.get_cog('StickyManager')
            if sticky_manager:
                await sticky_manager.set_sticky_message(
                    ctx.channel.id, message)
                await ctx.send("✅ Sticky message has been set!")
            else:
                await ctx.send("Sticky message manager is not available!")
        except Exception as e:
            await ctx.send(f"Failed to set sticky message: {str(e)}")

    @commands.command(name="spamcap")
    async def spamcap(self, ctx: commands.Context):
        """Show the current spam message limit"""
        await ctx.send(
            f"The current spam message limit is {self.spam_cap} messages. Use =spam @user [count] to send messages (1-{self.spam_cap})."
        )

    @commands.command(name="spam")
    async def spam(
            self,
            ctx: commands.Context,
            user: discord.Member,
            count: int = 5  # Default to 5 messages
    ):
        """Spam a user with 'AZURE MODDING IS COOL' messages in DM"""
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        # Lower max limit to 100 messages
        if count > self.spam_cap:  # Limit to prevent abuse
            await ctx.send(
                f"Maximum spam count is {self.spam_cap} messages. Setting count to {self.spam_cap}."
            )
            count = self.spam_cap

        try:
            # Create embed with our signature blue color
            embed = discord.Embed(description="AZURE MODDING IS COOL",
                                  color=discord.Color.blue())

            # Mark spam as active for this user
            self.spam_active[user.id] = True
            spam_stopped = False

            # Send multiple DMs
            for _ in range(count):
                # Check if spam was stopped
                if not self.spam_active.get(user.id, False):
                    spam_stopped = True
                    break
                await user.send(embed=embed)

            # Send appropriate completion message
            if spam_stopped:
                await ctx.send("Spam stopped by command.")
            else:
                await ctx.send("DM delivered super sigma!")
        except discord.Forbidden:
            await ctx.send("I don't have permission to DM this user!")
        except Exception as e:
            await ctx.send(f"Failed to send messages: {str(e)}")
        finally:
            # Clean up spam tracking
            self.spam_active.pop(user.id, None)

    @commands.command(name="spamstop")
    async def spamstop(self, ctx: commands.Context, user: discord.Member):
        """Stop ongoing spam for a user"""
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        if user.id in self.spam_active:
            self.spam_active[user.id] = False
            await ctx.send(f"Stopping spam for {user.mention}")
        else:
            await ctx.send(f"No active spam found for {user.mention}")

    @commands.command(name="warn")
    async def warn(self,
                   ctx: commands.Context,
                   user: discord.Member,
                   *,
                   reason: str = "No reason provided"):
        """Warn a user with a specified reason"""
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        try:
            # Store the warning
            if user.id not in self.warnings:
                self.warnings[user.id] = []

            self.warnings[user.id].append({
                'reason': reason,
                'timestamp': datetime.utcnow(),
                'warner_id': ctx.author.id
            })

            # Send warning in channel
            warn_embed = discord.Embed(
                description=
                f"✅ {user.mention} has been warned\nReason: {reason}",
                color=discord.Color.blue())
            await ctx.send(embed=warn_embed)

        except Exception as e:
            await ctx.send(f"Failed to warn user: {str(e)}")

    @commands.command(name="warns")
    async def warns(self, ctx: commands.Context, user: discord.Member):
        """Show warnings for a specific user"""
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        user_warnings = self.warnings.get(user.id, [])

        if not user_warnings:
            await ctx.send(f"No warnings found for {user.mention}")
            return

        # Create embed with all warnings
        embed = discord.Embed(title=f"Warnings for {user.name}",
                              color=discord.Color.blue())

        for i, warning in enumerate(user_warnings, 1):
            warner = ctx.guild.get_member(warning['warner_id'])
            warner_name = warner.name if warner else "Unknown"
            embed.add_field(
                name=f"Warning #{i}",
                value=
                f"Reason: {warning['reason']}\nBy: {warner_name}\nDate: {warning['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}",
                inline=False)

        await ctx.send(embed=embed)

    @commands.command(name="delwarning")
    async def delwarning(self, ctx: commands.Context, user: discord.Member):
        """Delete the latest warning from a user"""
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        try:
            if user.id not in self.warnings or not self.warnings[user.id]:
                await ctx.send(f"No warnings found for {user.mention}")
                return

            # Remove the latest warning
            removed_warning = self.warnings[user.id].pop()

            # If no warnings left, remove the user from warnings dict
            if not self.warnings[user.id]:
                del self.warnings[user.id]

            # Create confirmation embed
            embed = discord.Embed(
                description=
                f"✅ Removed warning from {user.mention}\nReason was: {removed_warning['reason']}",
                color=discord.Color.blue())
            await ctx.send(embed=embed)

        except Exception as e:
            await ctx.send(f"Failed to delete warning: {str(e)}")

    @commands.command(name="name")
    async def name(self, ctx: commands.Context, user: discord.Member, *,
                   new_name: str):
        """Change a user's nickname"""
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        try:
            # Store old name for confirmation message
            old_name = user.display_name

            # Change the nickname
            await user.edit(nick=new_name)

            # Send confirmation with embed
            embed = discord.Embed(
                description=
                f"✅ Changed {user.mention}'s nickname\nFrom: {old_name}\nTo: {new_name}",
                color=discord.Color.blue())
            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send(
                "I don't have permission to change this user's nickname!")
        except Exception as e:
            await ctx.send(f"Failed to change nickname: {str(e)}")

    @commands.command(name="role")
    async def role(self, ctx: commands.Context, user: discord.Member,
                   letter: str):
        """Add a role to a user using a letter identifier"""
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        # Map letters to role IDs
        role_map = {
            'm': 1338228572979990578,
            'M': 1338228572979990578,
            'a': 1339343222572318792,
            'A': 1339343222572318792,
            'dev': 1340040049156296714,
            'Dev': 1340040049156296714,
            'r': 1343766497624850564,
            'R': 1343766497624850564
        }

        if letter not in role_map:
            await ctx.send(
                "Invalid role letter! Use 'M/m', 'A/a', 'dev/Dev', or 'R/r'.")
            return

        try:
            role = ctx.guild.get_role(role_map[letter])
            if not role:
                await ctx.send("Role not found in this server!")
                return

            await user.add_roles(role)
            embed = discord.Embed(
                description=f"✅ Added role {role.name} to {user.mention}",
                color=discord.Color.blue())
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("I don't have permission to add roles!")
        except Exception as e:
            await ctx.send(f"Failed to add role: {str(e)}")

    @commands.command(name="roleremove")
    async def roleremove(self, ctx: commands.Context, user: discord.Member,
                         letter: str):
        """Remove a role from a user using a letter identifier"""
        if not await has_admin_permissions(ctx):
            await ctx.send("You don't have permission to use this command!")
            return

        # Map letters to role IDs
        role_map = {
            'm': 1338228572979990578,
            'M': 1338228572979990578,
            'a': 1339343222572318792,
            'A': 1339343222572318792,
            'dev': 1340040049156296714,
            'Dev': 1340040049156296714,
            'r': 1343766497624850564,
            'R': 1343766497624850564
        }

        if letter not in role_map:
            await ctx.send(
                "Invalid role letter! Use 'M/m', 'A/a', 'dev/Dev', or 'R/r'.")
            return

        try:
            role = ctx.guild.get_role(role_map[letter])
            if not role:
                await ctx.send("Role not found in this server!")
                return

            await user.remove_roles(role)
            embed = discord.Embed(
                description=f"✅ Removed role {role.name} from {user.mention}",
                color=discord.Color.blue())
            await ctx.send(embed=embed)
        except discord.Forbidden:
            await ctx.send("I don't have permission to remove roles!")
        except Exception as e:
            await ctx.send(f"Failed to remove role: {str(e)}")

    @commands.command(name="commands")
    async def show_commands(self, ctx: commands.Context):
        """Show all available commands"""
        embed = discord.Embed(
            title="Azure Modding Bot Commands",
            description="Here are all the available commands:",
            color=discord.Color.blue())

        # Moderation Commands
        mod_commands = (
            "`=ban @user [days] [reason]` - Ban a user from the server\n"
            "`=kick @user [reason]` - Kick a user from the server\n"
            "`=mute @user [duration] [reason]` - Timeout a user for specified duration\n"
            "`=warn @user [reason]` - Give a warning to a user\n"
            "`=warns @user` - View all warnings for a user\n"
            "`=delwarning @user` - Remove the latest warning\n"
            "`=name @user [new_name]` - Change a user's nickname\n"
            "`=role @user <M/m/A/a/dev/Dev/R/r>` - Add a role to a user\n"
            "`=roleremove @user <M/m/A/a/dev/Dev/R/r>` - Remove a role from a user\n"
            "\nRole Letters:\n"
            "• M/m - Member (1338228572979990578)\n"
            "• A/a - Admin (1339343222572318792)\n"
            "• dev/Dev - Developer (1340040049156296714)\n"
            "• R/r - Regular (1343766497624850564)\n"
            "\n`=lock` - Enable message blocking for muted roles\n"
            "`=unlock` - Disable message blocking\n"
            "`=afk [reason]` - Set yourself as AFK with required reason\n"
            "`=back` - Remove AFK status")
        embed.add_field(name="🛡️ Moderation", value=mod_commands, inline=False)

        # Spam Commands
        spam_commands = (
            "`=spam @user [count]` - Send specified number of DMs\n"
            "`=spamstop @user` - Stop sending DMs to user\n"
            "`=spamcap` - Show current spam message limit\n"
            "`=setspam [number]` - Set new spam message limit")
        embed.add_field(name="📨 Spam Controls",
                        value=spam_commands,
                        inline=False)

        # Other Commands
        other_commands = (
            "`=sticky [message]` - Set a sticky message in channel\n"
            "`=dm [message]` - DMs a user based on what message field is submitted\n"
            "`=say [message]` - Make the bot say something\n"
            "`=avatar [@user]` - Show a user's avatar, name, and account age\n"
            "`=funfact` - Generate a random fun fact\n"
            "`=info` - Show Azure Modding information\n"
            "`=ping` - Check bot's response time\n"
            "`=recent` - Get the link to our file downloads\n"
            "`=commands` - Display this help message")
        embed.add_field(name="ℹ️ Other", value=other_commands, inline=False)

        embed.set_footer(
            text=
            "Most commands require admin permissions except =say, =avatar, =funfact, =info, =ping, =recent, and =commands"
        )

        await ctx.send(embed=embed)

    @commands.command(name="afk")
    async def afk(self, ctx: commands.Context, *, reason: str):
        """Set yourself as AFK with a required reason"""
        try:
            # Store original nickname and reason
            original_nick = ctx.author.display_name
            self.afk_users[ctx.author.id] = {
                "nickname": original_nick,
                "reason": reason
            }

            # Change nickname to include [AFK]
            new_nick = f"[AFK] {original_nick}"
            if len(new_nick) > 32:  # Discord's nickname length limit
                new_nick = f"[AFK] {original_nick[:27]}"  # Truncate if too long

            await ctx.author.edit(nick=new_nick)
            embed = discord.Embed(
                description=f"✅ {ctx.author.mention} is now AFK: {reason}",
                color=discord.Color.blue())
            await ctx.send(embed=embed)

        except discord.Forbidden:
            await ctx.send("I don't have permission to change your nickname!")
        except Exception as e:
            await ctx.send(f"Failed to set AFK status: {str(e)}")

    @commands.command(name="back")
    async def back(self, ctx: commands.Context):
        """Remove your AFK status"""
        try:
            if ctx.author.id in self.afk_users:
                # Restore original nickname
                original_nick = self.afk_users[ctx.author.id]["nickname"]
                await ctx.author.edit(nick=original_nick)
                del self.afk_users[ctx.author.id]

                embed = discord.Embed(
                    description=f"✅ Welcome back {ctx.author.mention}!",
                    color=discord.Color.blue())
                await ctx.send(embed=embed)
            else:
                await ctx.send("You weren't AFK!")

        except discord.Forbidden:
            await ctx.send("I don't have permission to change your nickname!")
        except Exception as e:
            await ctx.send(f"Failed to remove AFK status: {str(e)}")

    @commands.command(name="say")
    async def say(self, ctx: commands.Context, *, message: str):
        """Make the bot say something"""
        # This command is available to everyone
        try:
            # Delete the command message
            await ctx.message.delete()
        except (discord.Forbidden, discord.NotFound):
            # Ignore if we can't delete the message
            pass

        # Send the message as the bot
        await ctx.send(message)

    @commands.command(name="avatar")
    async def avatar(self, ctx: commands.Context, user: discord.Member = None):
        """Show a user's avatar, name, and account age"""
        # If no user is specified, use the command author
        target_user = user or ctx.author

        # Calculate account age
        # Make both timezone aware to prevent "can't subtract offset-naive and offset-aware datetimes"
        now = datetime.utcnow().replace(tzinfo=None)
        account_created = target_user.created_at.replace(tzinfo=None)
        account_age = now - account_created

        # Format account age nicely
        years = account_age.days // 365
        months = (account_age.days % 365) // 30
        days = (account_age.days % 365) % 30

        if years > 0:
            age_str = f"{years} year{'s' if years != 1 else ''}, {months} month{'s' if months != 1 else ''}, {days} day{'s' if days != 1 else ''}"
        elif months > 0:
            age_str = f"{months} month{'s' if months != 1 else ''}, {days} day{'s' if days != 1 else ''}"
        else:
            age_str = f"{days} day{'s' if days != 1 else ''}"

        # Create an embed with user info
        embed = discord.Embed(
            title=f"{target_user.display_name}'s Avatar",
            description=
            f"**Username:** {target_user.name}\n**Account Age:** {age_str}\n**Created On:** {account_created.strftime('%Y-%m-%d %H:%M:%S')} UTC",
            color=discord.Color.blue())

        # Add the avatar as an image
        embed.set_image(url=target_user.display_avatar.url)

        # Add footer with the user's ID
        embed.set_footer(text=f"User ID: {target_user.id}")

        await ctx.send(embed=embed)

    @commands.command(name="funfact")
    async def funfact(self, ctx: commands.Context):
        """Generate a random fun fact"""
        try:
            # List of fun facts
            fun_facts = [
                "The shortest war in history was between Britain and Zanzibar in 1896, lasting only 38 minutes.",
                "A group of flamingos is called a 'flamboyance'.",
                "Honey never spoils. Archaeologists have found pots of honey in ancient Egyptian tombs that are over 3,000 years old and still perfectly good to eat.",
                "The world's oldest known living tree is a Great Basin Bristlecone Pine that is over 5,000 years old.",
                "Octopuses have three hearts, nine brains, and blue blood.",
                "A day on Venus is longer than a year on Venus. Venus takes 243 Earth days to rotate once on its axis but only 225 Earth days to orbit the Sun.",
                "The fingerprints of koalas are so similar to humans that they have on occasion been confused at crime scenes.",
                "The average person will spend six months of their life waiting for red lights to turn green.",
                "A bolt of lightning is five times hotter than the surface of the sun.",
                "Bananas grow upside down.",
                "The Eiffel Tower can be 15 cm taller during the summer due to thermal expansion.",
                "A group of crows is called a 'murder'.",
                "The Hawaiian alphabet has only 12 letters.",
                "A rhinoceros' horn is made of hair.",
                "Cats can't taste sweet things because they lack the needed taste receptors."
            ]

            # Select a random fun fact
            random_fact = random.choice(fun_facts)

            # Create embed with the fun fact
            embed = discord.Embed(title="Random Fun Fact",
                                  description=random_fact,
                                  color=discord.Color.blue())

            embed.set_footer(text="Fun Fact generated by Azure Modding Bot")

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(
                f"Error generating fun fact: {e}\nPlease try again or contact an admin if the issue persists."
            )

    @commands.command(name="commandsevery")
    async def commands_every(self, ctx: commands.Context):
        """Show commands that are accessible to everyone (not just admins)"""
        embed = discord.Embed(
            title="Commands For Everyone",
            description="Here are all the commands that everyone can use:",
            color=discord.Color.blue())

        everyone_commands = (
            "`=say [message]` - Make the bot say something\n"
            "`=avatar [@user]` - Show a user's avatar, name, and account age\n"
            "`=funfact` - Generate a random fun fact\n"
            "`=recent` - Get the link to our file downloads\n"
            "`=info` - Show Azure Modding information\n"
            "`=ping` - Check bot's response time\n"
            "`=commands` - Display all commands (including admin commands)\n"
            "`=commandsevery` - Display this help message")

        embed.add_field(name="Available Commands",
                        value=everyone_commands,
                        inline=False)
        embed.set_footer(
            text=
            "These commands can be used by everyone, no admin permissions required"
        )

        await ctx.send(embed=embed)

    @commands.command(name="recent")
    async def recent(self, ctx: commands.Context):
        """Display the GoFile link for downloads"""
        # Check if user has the Developer role (ID: 1340040049156296714)
        dev_role_id = 1340040049156296714
        has_dev_role = any(role.id == dev_role_id for role in ctx.author.roles)

        if not has_dev_role:
            await ctx.send(
                "You don't have permission to use this command! Developer role required."
            )
            return

        embed = discord.Embed(
            title="Azure Modding File Download",
            description="Click the link below to access our files:",
            color=discord.Color.blue())

        embed.add_field(name="Download Link",
                        value="[GoFile Download](https://gofile.io/d/FObqDl)",
                        inline=False)

        embed.set_footer(text="Azure Modding • Files hosted on GoFile")

        await ctx.send(embed=embed)

    @commands.command(name="commandsevery")
    async def commands_every(self, ctx: commands.Context):
        """Show commands that are accessible to everyone (not just admins)"""
        embed = discord.Embed(
            title="Commands For Everyone",
            description="Here are all the commands that everyone can use:",
            color=discord.Color.blue())

        everyone_commands = (
            "`=say [message]` - Make the bot say something\n"
            "`=avatar [@user]` - Show a user's avatar, name, and account age\n"
            "`=funfact` - Generate a random fun fact\n"
            "`=recent` - Get the link to our file downloads\n"
            "`=info` - Show Azure Modding information\n"
            "`=ping` - Check bot's response time\n"
            "`=commands` - Display all commands (including admin commands)\n"
            "`=commandsevery` - Display this help message")

        embed.add_field(name="Available Commands",
                        value=everyone_commands,
                        inline=False)
        embed.set_footer(
            text=
            "These commands can be used by everyone, no admin permissions required"
        )

        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))
