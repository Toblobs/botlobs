# cogs > staff_commands.py // @toblobs // 21.03.26

from datetime import timedelta
import time
from .__init__ import *

import re
import io
import asyncio
import math

from typing import List, Tuple

from discord import app_commands
from discord.ext import commands
from discord.utils import remove_markdown, escape_mentions

import numpy as np

from PIL import Image

from cogs import get_top_colored_role, upload_asset
from cogs.utils.embeds import basic_embed
from cogs.utils.permissions import *

from database import dbio, reward_roles, reminders, users, rank, quotes
from database import xp as experience

class StaffCommands(commands.Cog):

    DELETE_MAP = {
        "no-deletion": 0,
        "prev-hour": 3600,
        "prev-6-hours": 21600,
        "prev-12-hours": 43200,
        "prev-24-hours": 86400,
        "prev-3-days": 259200,
        "prev-7-days": 604800
    }
    
    def __init__(self, bot: commands.Bot, wakeup: asyncio.Event):

        self.bot = bot
        self.wakeup = wakeup
        
    ### generally used submodules

    ### commands
    
    # /xp-set
    @app_commands.command(name = "xp-set", description = "Modifies the XP of a member.")
    @app_commands.choices(operation = [app_commands.Choice(name = "Set XP", value = "set"), app_commands.Choice(name = "Add XP", value = "add"), app_commands.Choice(name = "Subtract XP", value = "subtract"), app_commands.Choice(name = "Add Levels", value = "add-levels"), app_commands.Choice(name = "Subtract Levels", value = "subtract-levels"),
                                       app_commands.Choice(name = "Add %", value = "add-percentage"), app_commands.Choice(name = "Subtract %", value = "subtract-percentage"), app_commands.Choice(name = r"Add % of Bucket", value = "add-bucket"), app_commands.Choice(name = r"Subtract % of Bucket", value = "subtract-bucket")])
    @app_commands.describe(member = "The member to modify the XP of", amount = "The number to operate with", operation = "The operation to perform, optional", bucket = r"The bucket of members to get a % of, optional")
    async def xp_set(self, interaction: discord.Interaction, member: discord.Member, amount: int, operation: app_commands.Choice[str] = "set", bucket: int = 10): # type: ignore
        
        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"This command must be used from a text channel.", bot = self.bot), ephemeral = True)
            return
        
        if operation == "set":
            _op = "set"
            _op_name = "Set XP"
            
        else:
            _op = operation.value
            _op_name = operation.name
        
        current_xp, level, prestige, intro_text, birthday, country = await users.get_user(member.id) # type: ignore
        
        if (current_xp == None) or (level == None):
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not fetch XP info about this member.", bot = self.bot), ephemeral = True)
            return
        
        if not (0 < bucket < await rank.total_users()):
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Bucket is too large/small, must be between `1` and `{await rank.total_users()}`.", bot = self.bot), ephemeral = True)
            return
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        if not is_moderator(interaction.user): # type: ignore

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        name = member.name
        mention = member.mention
        
        final_xp = 0
        
        match _op:
            
            case "set": final_xp = amount
            
            case "add": final_xp = current_xp + amount
            
            case "subtract": final_xp = current_xp - amount
            
            case "add-levels":  final_xp = current_xp + (experience.xp_required(level = level + amount) - experience.xp_required(level = level))
            
            case "subtract-levels": final_xp = current_xp - (experience.xp_required(level = level) - experience.xp_required(level = level - amount))
            
            case "add-percentage": final_xp = current_xp + int((amount / 100) * current_xp)
            
            case "remove-percentage": final_xp = current_xp - int((amount / 100) * current_xp)
            
            case "add-bucket": final_xp = current_xp + int((amount / 100) * await experience.get_top_xp_sum(bucket))
            
            case "remove-bucket": final_xp = current_xp - int((amount / 100) * await experience.get_top_xp_sum(bucket))

        if final_xp < 0:
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"The result of the operation leads to a negative XP amount.", bot = self.bot), ephemeral = True)
            return
        
        else:
            
            thumbnail_link = f"https://twemoji.maxcdn.com/v/latest/72x72/{ord("💫"):x}.png"
            message = await interaction.response.send_message(embed = basic_embed(title = "XP Set", description = f"XP Modified for {mention}\n> - **Original XP**: `{current_xp:,}`\n> - **Final XP**: `{final_xp:,}`\n> - **XP Change**: `{(final_xp - current_xp):,}`\n> - **Operation**: `{_op_name}`", bot = self.bot, thumbnail = thumbnail_link))

            
            await experience.set_xp(member.id, final_xp, self.bot)
            await experience.add_mod_action(message.id, member.id, interaction.channel.id, int(datetime.now().timestamp()), (final_xp - current_xp), _op, interaction.user.id) # type: ignore

    # /multipliers-set
    @app_commands.command(name = "multipliers-set", description = " Modifies the XP boost multipliers")
    @app_commands.describe(role = "The role multiplier to modify, optional", channel = "The channel multiplier to modify, optional", multiplier = "The multiplier to set to", remove = "Toggles deleting this multiplier, optional")
    async def multipliers_set(self, interaction: discord.Interaction, multiplier: str, role: discord.Role | None = None, channel: discord.TextChannel | discord.CategoryChannel | None = None, remove: bool = False):
        
        if not is_moderator(interaction.user): # type: ignore
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return

        try:
            
            float_mult = float(multiplier)
            assert 0 <= float_mult <= 1000, "Provided multiplier is not between 0 and 1000."
        
        except Exception as e: 
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True) # type: ignore
            return
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        cur = await dbio.db.conn.execute("""
            SELECT role_id, channel_id, multiplier
            FROM multipliers
        """)

        rows = await cur.fetchall()
        found = False
        
        our_role_id = role.id if role else 0
        our_channel_id = channel.id if channel else 0
        
        for (role_id, channel_id, multiplier) in rows:
            
            if role_id == our_role_id and our_role_id != None:
                
                found = True
                
                await cur.execute("""
                    UPDATE multipliers
                    SET multiplier = ?
                    WHERE role_id = ?
                """, (float_mult, role_id,))
                
                await interaction.response.send_message(embed = basic_embed(title = "Multiplier Set", description = f"Multiplier for {role.mention if role else "???"} set to `({float_mult})x`", bot = self.bot)) # type: ignore
            
            elif channel_id == our_channel_id and our_channel_id != None:
                
                found = True
                
                await cur.execute("""
                    UPDATE multipliers
                    SET multiplier = ?
                    WHERE channel_id = ?
                """, (float_mult, channel_id,))
                
                await interaction.response.send_message(embed = basic_embed(title = "Multiplier Set", description = f"Multiplier for {channel.mention if channel else "???"} set to `({float_mult})x`", bot = self.bot)) # type: ignore
                
        if not found:
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Role/channel multiplier not found.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
               
    # /nick-set
    @app_commands.command(name ="nick-set", description = "Sets the nickname of a member.")
    @app_commands.describe(member = "The member to set the nickname of", nick = "The nickname to set")
    async def nick_set(self, interaction: discord.Interaction, member: discord.Member, nick: str):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        if not is_staff(interaction.user): # type: ignore
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(JR_MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        try: 
            
            await member.edit(nick = nick)
            await interaction.response.send_message(embed = basic_embed(title = "Nickname Set", description = f"Nickname for {member.mention} set to `{nick}`.", bot = self.bot), allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
        
        except Exception as e: 
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True) # type: ignore
            return
        
    # /mute
    @app_commands.command(name = "mute", description = "Mutes a member.")
    @app_commands.describe(member = "The member to mute", duration = "The time to mute them for, optional", reason = "The reason given for muting them, optional", solitary = "A toggle to move them to solitary confinement, optional", decay = "Whether to remove muted/solitary role from them after timeout, optional")
    async def mute(self, interaction: discord.Interaction, member: discord.Member, duration: str = "10m", reason: str = "", solitary: bool = False, decay: bool = True):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        await interaction.response.defer()
        
        if not is_staff(interaction.user): # type: ignore

            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(JR_MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        if is_staff(member) and not is_staff_supersede(interaction.user, member): # type: ignore
            
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"You cannot use this command on a staff member higher or equal to you in the heirarchy.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return

        try:
            
            delta = parse_time_string(duration)
        
        except ValueError as e:
            
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True) 
            return
        
        now = datetime.now()
        
        td = now + timedelta(days = 28)
        rd = now + delta
    
        if rd > td:
            
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Mute `duration` cannot exceed `28` days.", bot = self.bot), ephemeral = True) 
            return
    
        muted_role = guild.get_role(1140287361352204339) # type: ignore
        await member.add_roles(muted_role, reason = reason) # type: ignore
        
        final_delta = (now + delta) - (now)
        end_timestamp = int(rd.timestamp())
        
        try: await member.timeout(final_delta)
        except Exception: pass
        
        # Solitary confinement
        if solitary:
            
            solitary_channel = guild.get_channel(1140287255001432217) # type: ignore
            solitary_role = guild.get_role(1140287435809497108) # type: ignore
            await solitary_channel.purge(limit = 1000) # type: ignore
            await member.add_roles(solitary_role, reason = reason) # type: ignore
        
        # Try DM member
        try: await member.send(embed = basic_embed(title = "Muted Information", description = f"You have been muted in **{guild.name}** for `{duration}`.\nReason: {reason if reason else "None given."}", bot = self.bot)) # type: ignore
        except Exception: pass
        
        if decay:
            await reminders.add_reminder(user_id = BOT_ID, timestamp = end_timestamp, channel_id = BOT_LOGS_CHANNEL, message = f"unmute:{member.id}", repeat = False) # type: ignore
            self.wakeup.set() 
        
        await interaction.followup.send(embed = basic_embed(title = "Muted Member", description = f"Muted {member.mention} for `{duration}`.", bot = self.bot))
        
    # /unmute
    @app_commands.command(name = "unmute", description = "Unmutes a member.")
    @app_commands.describe(member = "The member to unmute")
    async def unmute(self, interaction: discord.Interaction, member: discord.Member):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        await interaction.response.defer()
        
        if not is_staff(interaction.user): # type: ignore

            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(JR_MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        if is_staff(member) and not is_staff_supersede(interaction.user, member): # type: ignore
            
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"You cannot use this command on a staff member higher or equal to you in the heirarchy.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        due_reminders = await reminders.get_due_reminders()
        
        reminder = None
        
        for d in due_reminders:
            if str(d[5]) == f"unmute:{member.id}":
                reminder = d
        
        if (reminder) and (member.is_timed_out()):
            
            await member.edit(timed_out_until = None)
            
            await reminders.delete_reminder(int(reminder[0]))
            
            muted_role = guild.get_role(1140287361352204339) # type: ignore 
            solitary_role = guild.get_role(1140287435809497108) # type: ignore

            if muted_role in member.roles: await member.remove_roles(muted_role) # type: ignore
            if solitary_role in member.roles: await member.remove_roles(solitary_role) # type: ignore
            
            await interaction.followup.send(embed = basic_embed(title = "Unmuted Member", description = f"Member unmuted completely.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        elif (not reminder) and (not member.is_timed_out()):
            
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"This member wasn't muted or timed out.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
                
        elif (not reminder) and (member.is_timed_out()):
            
            await member.edit(timed_out_until = None)
            
            await interaction.followup.send(embed = basic_embed(title = "Unmuted Member", description = f"Member timeout removed (they were not muted via `/mute`).", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        elif (reminder) and (not member.is_timed_out()):
            
            await reminders.delete_reminder(int(reminder[0]))
            
            muted_role = guild.get_role(1140287361352204339) # type: ignore 
            solitary_role = guild.get_role(1140287435809497108) # type: ignore

            if muted_role in member.roles: await member.remove_roles(muted_role) # type: ignore
            if solitary_role in member.roles: await member.remove_roles(solitary_role) # type: ignore

            await interaction.followup.send(embed = basic_embed(title = "Unmuted Member", description = f"Member muted/solitary roles removed (they were not timed out at the time).", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
    
    # /kick
    @app_commands.command(name = "kick", description = "Kicks a member.")
    @app_commands.describe(member = "The member to kick", reason = "The reason given for kicking them, optional")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = ""): # type: ignore
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        await interaction.response.defer()
        
        if not is_staff(interaction.user): # type: ignore

            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(JR_MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        if is_staff(member) and not is_staff_supersede(interaction.user, member): # type: ignore
            
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"You cannot use this command on a staff member higher or equal to you in the heirarchy.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
    
        # Try DM member
        try: await member.send(embed = basic_embed(title = "Kicked Information", description = f"You were kicked from **{guild.name}**.\nReason: {reason}", bot = self.bot)) # type: ignore
        except Exception: pass
        
        await member.kick(reason = reason)
        
        await interaction.followup.send(embed = basic_embed(title = "Kicked Member", description = f"Kicked {member.mention}.", bot = self.bot))
                
    # /ban
    @app_commands.command(name = "ban", description = "Bans a member.")
    @app_commands.describe(member = "The member to ban", duration = "The time to ban them for, optional", reason = "The reason given fo banning them, optional", delete_messages = "Deletion of messages, optional")
    @app_commands.choices(delete_messages = [app_commands.Choice(name = "Don't Delete Any", value = "no-deletion"), app_commands.Choice(name = "Previous Hour", value = "prev-hour"), app_commands.Choice(name = "Previous 6 Hours", value = "prev-6-hours"), app_commands.Choice(name = "Previous 12 Hours", value = "prev-12-hours"),
                                             app_commands.Choice(name = "Previous 24 Hours", value = "prev-24-hours"), app_commands.Choice(name = "Previous 3 Days", value = "prev-3-days"), app_commands.Choice(name = "Previous 7 Days", value = "prev-7-days")])
    async def ban(self, interaction: discord.Interaction, member: discord.Member, duration: str = "10m", reason: str = "", delete_messages: app_commands.Choice[str] = "no-deletion"): # type: ignore
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        await interaction.response.defer()
        
        if not is_moderator(interaction.user): # type: ignore

            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        if is_staff(member) and not is_staff_supersede(interaction.user, member): # type: ignore
            
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"You cannot use this command on a staff member higher or equal to you in the heirarchy.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        try:
            
            delta = parse_time_string(duration)
        
        except ValueError as e:
            
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True) 
            return
        
        now = datetime.now()
        
        td = now + timedelta(days = 28)
        rd = now + delta
    
        if rd > td:
            
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Ban `duration` cannot exceed `28` days.", bot = self.bot), ephemeral = True) 
            return
    
        final_delta = (now + delta) - (now)
        end_timestamp = int(rd.timestamp())
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        delete_seconds = self.DELETE_MAP.get(delete_messages.value, 0)
        delete_days = min(delete_seconds // 86400, 7)
        
         # Try DM member
        try: await member.send(embed = basic_embed(title = "Banned Information", description = f"You were banned from **{guild.name}** for `{duration}`.\nReason: {reason if reason else "None given."}", bot = self.bot)) # type: ignore
        except Exception: pass
        
        await guild.ban(member, reason = reason, delete_message_days = delete_days) # type: ignore
        await reminders.add_reminder(user_id = BOT_ID, timestamp = end_timestamp, channel_id = BOT_LOGS_CHANNEL, message = f"unban:{member.id}", repeat = False) # type: ignore
        self.wakeup.set() 
        
        await interaction.followup.send(embed = basic_embed(title = "Banned Member", description = f"Banned {member.mention} for `{duration}`.", bot = self.bot))
        
    # /giveaway
    @app_commands.command(name = "giveaway", description = "Creates a server giveaway.")
    async def giveaway(self, interaction: discord.Interaction):
        
        if not is_moderator(interaction.user): # type: ignore

            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        member = interaction.user # type: ignore
        
        class GiveawayModal(discord.ui.Modal):
            
            def __init__(self, bot, wakeup: asyncio.Event):
                
                super().__init__(title = "Giveaway Form")
                
                self.add_item(discord.ui.TextInput(label = "Name", placeholder = "The name or topic of the giveaway...", style = discord.TextStyle.short))
                self.add_item(discord.ui.TextInput(label = "Duration", placeholder = "The time until the giveaway is conducted... (format like '1h30m', '2d')"))
                self.add_item(discord.ui.TextInput(label = "Description", placeholder = "More detail on the giveaway other than name...", style = discord.TextStyle.paragraph, required = False))
                self.add_item(discord.ui.TextInput(label = "Winner Amount", placeholder = "The amount of prize units to give out", style = discord.TextStyle.short, required = False))
                self.add_item(discord.ui.TextInput(label = "Role Ping", placeholder = "The role ID of a role to ping, e.g. 1203257064646901790 for Video Games", style = discord.TextStyle.short, required = False))
                
                self.bot = bot
                self.wakeup = wakeup
                
            async def on_submit(self, interaction: discord.Interaction):
                
                name = self.children[0].value # type: ignore
                duration = self.children[1].value # type: ignore
                description = self.children[2].value # type: ignore
                winner_amount = self.children[3].value # type: ignore
                role_id = self.children[4].value # type: ignore
                
                try:

                    assert len(name) < 30, "Length of name should not be more than `30` characters."
                    
                    try: duration = parse_time_string(duration)
                    except ValueError as e: raise AssertionError(str(e))
                    
                    if winner_amount != "":
                        try: winner_amount = int(winner_amount)
                        except ValueError: raise AssertionError("Can't convert `winner_amount` into an integer.")

                    else: winner_amount = 1
                    
                    if role_id != "":
                        assert guild.get_role(int(role_id)) != None, "Could not find a `role` with this role ID." # type: ignore
                    
                except BaseException as e:
                    
                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
                    return
                
                target_date = int((datetime.now() + duration).timestamp())
                events_channel = guild.get_channel(1140054643729252422) # type: ignore

                role = None
                if role_id != -1: role = guild.get_role(int(role_id)) # type: ignore
                
                message = await events_channel.send(f"{role.mention if role else ""}",  # type: ignore
                                                    embed = basic_embed(title = f"Giveaway: {name}", description = f"{member.mention} is holding a giveaway!\n> - **Giveaway Description**: {description}\n> - **Winner(s) Count**: {winner_amount}\n> - **Giveaway End Date/Time**: {f"<t:{target_date}:D> (<t:{target_date}:R>)"}{f"\n > - **Roles to Enter**: {role.mention}" if role else ""}", # type: ignore
                                                    bot = self.bot, 
                                                    thumbnail = f"https://twemoji.maxcdn.com/v/latest/72x72/{ord("🎆"):x}.png"),
                                                    allowed_mentions = discord.AllowedMentions(roles = True, everyone = True)) 

                await reminders.add_reminder(BOT_ID, target_date, events_channel.id, message = f"giveaway:{message.id}:{role_id}:{winner_amount}", repeat = None) # type: ignore
                self.wakeup.set()
                
                await interaction.response.send_message(embed = basic_embed(title = "Giveaway Form", description = f"Giveaway scheduled.", bot = self.bot), ephemeral = True)
    
        await interaction.response.send_modal(GiveawayModal(bot = self.bot, wakeup = self.wakeup))
                
    # /purge
    @app_commands.command(name = "purge", description = "Purges messages in a channel.")
    @app_commands.describe(after = "The message link to delete messages after from", count = "The amount of messages to delete, optional", match = "Whether to only delete messages with a certain case-insensitive phrase, given in a comma seperated list like [balls, jingle], optional", 
                           member = "The member to selectively delete messages from, optional", bots = "Whether to only delete messages from bots, optional", embeds = "Whether to only delete messages containing embeds, optional", 
                           mentions = "Whether to only delete messages with any mentions, optional", links = "Whether to only delete messages containing links, optional", invites = "Whether to only delete messages containing invite links, optional", images = "Whether to only delete messages containing images, optional")
    async def purge(self, interaction: discord.Interaction, after: str, count: int | None, match: str | None = None, member: discord.Member | None = None, bots: bool = False, embeds: bool = False, mentions: bool = False, links: bool = False, invites: bool = False, images: bool = False):
        
        await interaction.response.defer()
        
        if not is_moderator(interaction.user): # type: ignore

            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        if not isinstance(interaction.channel, discord.TextChannel):
            
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"This command should be used in the text channel to purge.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) 
            return
        
        INVITE_REGEX = re.compile(r"(discord\.gg|discord\.com/invite)")
        LINK_REGEX = re.compile(r"https?://")
        
        def parse_message_link(link: str):

            try: return int(link.split('/')[-1])
            except: return None
        
        def parse_match(match: str | None):
            
            if not match: return []
            match = match.strip("[]")
            return [m.strip().lower() for m in match.split(",")]
        
        if count is None: count = 100
        count = min(count, 1000)
        
        after_id = parse_message_link(after) if after else None
        match_list = parse_match(match)
        
        deleted = []
        scanned = 0
        
        async for msg in interaction.channel.history(limit = 1000): 
            
            scanned += 1
            
            if after_id and msg.id <= after_id: break
            if len(deleted) >= count: break
            
            # Filters
            if member and msg.author != member: continue
            if bots and not msg.author.bot: continue
            if embeds and not msg.embeds: continue
            if mentions and not msg.mentions: continue
            if links and not LINK_REGEX.search(msg.content): continue
            if invites and not INVITE_REGEX.search(msg.content): continue
            
            if images:
                if not any(a.content_type and "image" in a.content_type for a in msg.attachments): continue
            
            if match_list:
                if not any(word in msg.content.lower() for word in match_list): continue
            
            deleted.append(msg)
        
        if not interaction.response.is_done(): await interaction.followup.send(content = "Done computation.")
        
        async for msg in interaction.channel.history(limit = 1):
            await interaction.channel.delete_messages([msg,]) # get rid of bot message

        try:
            for i in range(0, len(deleted), 100):
                await interaction.channel.delete_messages(deleted[i:i + 100])
                
        except Exception as e:
            await interaction.channel.send(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot))
        
        else: 
            await interaction.channel.send(embed = basic_embed(title = "Purge Messages", description = f"Successfully deleted `{len(deleted)}` messages matching criteria in {interaction.channel.mention}", bot = self.bot))
        
    # /lock
    @app_commands.command(name = "lock", description = "Lock a given channel.")
    @app_commands.describe(channel = "The channel to lock", message = "The message to send on the lock embed", duration = "The time to lock them for, optional", reactions = "Whether to allow members to react to messages while channel is locked, optional")
    async def lock(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel, duration: str = "1h", reactions: bool = False):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        await interaction.response.defer()
        
        if not is_moderator(interaction.user): # type: ignore

            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        try:
            
            delta = parse_time_string(duration)
        
        except ValueError as e:
            
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True) 
            return
        
        now = datetime.now()
        
        td = now + timedelta(days = 7)
        rd = now + delta
    
        if rd > td:
            
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Lock `duration` cannot exceed `7` days.", bot = self.bot), ephemeral = True) 
            return
        
        end_timestamp = int(rd.timestamp())

        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        for mod_role in [guild.get_role(s) for s in staff]: # type: ignore
            mod_overwrite = channel.overwrites_for(mod_role) # type: ignore
            mod_overwrite.send_messages = mod_overwrite.add_reactions = True
            await channel.set_permissions(mod_role, overwrite = mod_overwrite) # type: ignore
            
        everyone = guild.default_role # type: ignore
        overwrite = channel.overwrites_for(everyone)
        overwrite.send_messages = False
        if not reactions: overwrite.add_reactions = False
        
        await channel.set_permissions(everyone, overwrite = overwrite)
        
        lock_msg: discord.Message = await interaction.followup.send(embed = basic_embed(title = "Channel Locked", description = f"🔒 This channel has been locked by {interaction.user.mention}.\n> - **Message**: {message}\n> - **Time Locked**: `{duration}` (<t:{end_timestamp}:R>)", bot = self.bot)) # type: ignore

        await reminders.add_reminder(user_id = BOT_ID, timestamp = end_timestamp, channel_id = BOT_LOGS_CHANNEL, message = f"unlock:{channel.id}:{lock_msg.id}", repeat = False) # type: ignore
        self.wakeup.set() 
        
        await lock_msg.add_reaction("🔑") # type: ignore
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):  
        
        if str(payload.emoji) != "🔑":
            return
    
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        member = guild.get_member(payload.user_id)  # type: ignore
        locked_channel: discord.TextChannel = guild.get_channel(payload.channel_id) # type: ignore

        if member.bot: return # type: ignore
        
        all_reminders = await reminders.get_due_reminders()
        
        for a in all_reminders:
            
            message_id = int(str(a[5]).split(":")[2])
            
            if payload.message_id == message_id:
                
                if not is_moderator(member): # type: ignore
            
                    message_id = int(str(a[5]).split(":")[2])
                    message = locked_channel.get_partial_message(message_id)
                    await message.remove_reaction(member = member, emoji = "🔑") # type: ignore
                    return

                everyone = guild.default_role # type: ignore
                overwrite = locked_channel.overwrites_for(everyone)
                overwrite.send_messages = None
                overwrite.add_reactions = None
                
                await locked_channel.set_permissions(everyone, overwrite = overwrite)
                
                for mod_role in [guild.get_role(s) for s in staff]: # type: ignore
                    mod_overwrite = locked_channel.overwrites_for(mod_role) # type: ignore
                    mod_overwrite.send_messages = mod_overwrite.add_reactions = None
                    await locked_channel.set_permissions(mod_role, overwrite = mod_overwrite) # type: ignore
                    
                await locked_channel.send(embed = basic_embed(title = "Channel Unlocked", description = "🔓 Channel unlocked.", bot = self.bot))
                await reminders.delete_reminder(int(a[0]))

    # /quote-bank
    @app_commands.command(name = "quote-bank", description = "Search or modify the quote bank.")
    @app_commands.describe(member = "The member to show all quotes for, optional", remove = "The message ID to remove a quote from, optional")
    async def quote_bank(self, interaction: discord.Interaction, member: discord.Member | None = None, remove: str = ""):
        
        await interaction.response.defer()
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        if not is_staff(interaction.user): # type: ignore

            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(JR_MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        if remove == "":
        
            if member: all_quotes = list(await quotes.get_member_quotes(user_id = member.id))
            else: all_quotes = list(await quotes.get_all_quotes())

            all_length = len(all_quotes)

            description = "**Quote ID | Quote Author | Quote Description**\n"
            
            for (a_quote_id, a_user_id, a_message_id, a_content, a_timestamp) in all_quotes[:25]:
                
                quote_author = guild.get_member(a_user_id) # type: ignore
                date = datetime.fromtimestamp(int(a_timestamp))
                
                content = escape_mentions(remove_markdown(a_content))
                
                description += f"`{a_quote_id}` | {quote_author.mention if quote_author else "???"} | {content}\n" # type: ignore

            if all_length > 25: 
                
                description += " ... (showing first **25** quotes)"
                
            await interaction.followup.send(embed = basic_embed(title = "Quote Bank", description = description, bot = self.bot), allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
        
        else:
            
            await quotes.delete_quote(int(remove))
            
            await interaction.followup.send(embed = basic_embed(title = "Quote Bank", description = f"Quote with ID `{int(remove)}` has been removed from the database.", bot = self.bot)) # type: ignore
            
            
    # /custom-set
    @app_commands.command(name = "custom-set", description = "Create or remove custom roles.")
    @app_commands.describe(member = "The member to modify the custom of", role = "The discord role to set as a custom, if it exists", name = "The name of the role", hexes = "Either a single hex like #0f0f0f, or formatted in a comma-separated list like [#0f0f0f,#1f1f1f]", color = "The black tie color pathway this custom is on", icon = "The role icon, optional", remove = "Toggling removal of the custom and role if they exist")
    async def custom_set(self, interaction: discord.Interaction, member: discord.Member, color: str, role: discord.Role | None = None, name: str | None = None, hexes: str | None = None, icon: discord.Attachment | None = None, remove: bool = False):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore

        if not is_moderator(interaction.user): # type: ignore

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return

        colors_list = ["red", "orange", "yellow", "green", "blue", "purple", "monochrome"]
        gen_cog = self.bot.get_cog("GeneralCommands")

        if color not in colors_list:

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"`color` must be in {', '.join([f"`{c}`" for c in colors_list])}", bot = self.bot), ephemeral = True)
            return

        if icon and not ("ROLE_ICONS" in interaction.guild.features): # type: ignore

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"The server currently doesnt have server icons unlocked. Please don't provide a role icon.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore

        if not remove:
            
            if role and name:

                try:

                    hexes_list = gen_cog.parse_colors(hexes, max_colors = 2) # type: ignore

                    if not ("ENHANCED_ROLE_COLORS" in interaction.guild.features) and len(hexes_list) > 1: # type: ignore
                        await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"The server currently doesn't have gradient roles unlocked. Please input a single hex.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
                        return

                except ValueError as e:

                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
                    return
                    
                rgbs_list = [gen_cog.hex_to_rgb(h) for h in hexes_list] # type: ignore

                await reward_roles.add_custom(role.id, member.id, color)

                await role.edit(name = name, color = discord.Color.from_rgb(*rgbs_list[0]), secondary_color = discord.Color.from_rgb(*rgbs_list[1]) if len(rgbs_list) > 1 else None, position = guild.get_role(1237475644150124604).position) # type: ignore

                await interaction.response.send_message(embed = basic_embed(title = "Custom Edited", description = f"{role.mention} has been edited for {member.mention}.", bot = self.bot), allowed_mentions = discord.AllowedMentions(roles = True))

            if role and icon:

                icon_binary = None
            
                try:

                    icon_binary = await get_icon_binary(icon)
                
                except ValueError as e:
                    
                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True))

                role_icon = io.BytesIO(icon_binary) if icon_binary else None

                if role_icon: await role.edit(display_icon = icon_binary) # type: ignore

            if role: 
                
                await reward_roles.add_custom(role.id, member.id, color)
                
                await interaction.response.send_message(embed = basic_embed(title = "Custom Added", description = f"{role.mention} has been added to {member.mention} and backend custom table.", bot = self.bot), allowed_mentions = discord.AllowedMentions(roles = True))
            
            else:

                if not name:

                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"One of `role` and `name` must be provided.", bot = self.bot), ephemeral = True)
                    return
                
                try:

                    hexes_list = gen_cog.parse_colors(hexes, max_colors = 2) # type: ignore

                except ValueError as e:

                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
                    return

                rgbs_list = [gen_cog.hex_to_rgb(h) for h in hexes_list] # type: ignore

                role = await guild.create_role(name = name, color = discord.Color.from_rgb(*rgbs_list[0]), secondary_color = discord.Color.from_rgb(*rgbs_list[1]) if len(rgbs_list) > 1 else None) # type: ignore
                await role.edit(position = guild.get_role(1237475644150124604).position) # type: ignore
                
                await reward_roles.add_custom(role.id, member.id, color) # type: ignore
                await member.add_roles(role) # type: ignore

                await interaction.response.send_message(embed = basic_embed(title = "Custom Added", description = f"{role.mention} has been added to {member.mention} and backend custom table.", bot = self.bot), allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore

        else:

            if role:

                await reward_roles.remove_custom(role.id)
                await interaction.response.send_message(embed = basic_embed(title = "Custom Removed", description = f"`{role.name}` has been removed from {member.mention} and backend custom table.", bot = self.bot), allowed_mentions = discord.AllowedMentions(roles = True))
                await role.delete()

            else:

                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Role to delete must be provided.", bot = self.bot))
    
    # /remove-reminder
    @app_commands.command(name = "remove-reminder", description = "Remove reminders.")
    @app_commands.describe(reminder_id = "The ID of the reminder to remove")
    async def remove_reminder(self, interaction: discord.Interaction, reminder_id: int):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore

        if not is_moderator(interaction.user): # type: ignore

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Using this command is a permission for {guild.get_role(MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        reminder = await reminders.get_reminder(reminder_id) # type: ignore
        
        if reminder:
            
            await reminders.delete_reminder(reminder_id)
            await interaction.response.send_message(embed = basic_embed(title = "Reminder Deleted", description = f"Deleted reminder `{reminder_id}`.", bot = self.bot)) # type: ignore
        
        else:
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not find reminder ID `{reminder_id}`.", bot = self.bot), ephemeral = True) # type: ignore
            return