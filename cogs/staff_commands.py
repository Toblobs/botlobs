# cogs > staff_commands.py // @toblobs // 07.03.26

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

import numpy as np

from PIL import Image

from cogs import get_top_colored_role, upload_asset
from cogs.utils.embeds import basic_embed
from cogs.utils.permissions import *

from database import dbio, reward_roles, xp, reminders

class StaffCommands(commands.Cog):

    def __init__(self, bot: commands.Bot):

        self.bot = bot

    ### generally used submodules

    ### commands
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