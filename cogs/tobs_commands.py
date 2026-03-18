# cogs > tobs_commands.py // @toblobs // 18.03.26

from datetime import timedelta
from zoneinfo import ZoneInfo
import time
from .__init__ import *
import ast

import re
import io
import asyncio
import textwrap

from typing import List, Tuple

from discord import app_commands
from discord.ext import commands
from discord.utils import remove_markdown, escape_mentions

import numpy as np
import random

from database.dbio import db

from cogs import get_top_colored_role, upload_asset
from cogs.utils.embeds import basic_embed
from cogs.utils.permissions import *
from cogs.utils.music import *

from database import users, statuses

class TobsCommands(commands.Cog):
    
    def __init__(self, bot: commands.Bot, wakeup: asyncio.Event):
        
        self.bot = bot
        self.wakeup = wakeup
        
    ### generally used submodules
    
    ### commands
    
    # /status
    @app_commands.command(name = "status", description = "View the daily status update history.")
    @app_commands.describe(date = "The date to look for in YYYY-MM-DD format, optional", num = "The status number to look for, optional", match = "The first matching text to look for, optional", modify = "Modify a previous status when given date or num, optional")
    async def status(self, interaction: discord.Interaction, num: int | None = None, date: str | None = None, match: str | None = None, modify: str | None = None):
        
        await interaction.response.defer()

        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        toblobs_role = guild.get_role(TOBLOBS_ROLE) # type: ignore
        
        if not toblobs_role in interaction.user.roles: # type: ignore
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"This command is reserved for {toblobs_role.mention}.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        if num == date == match == None:
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"At least one of `num`, `date` and `match` must be provided.", bot = self.bot), ephemeral = True) # type: ignore
            return
        
        timestamp = None
        
        if date:
            
            try: 
                _date = datetime.strptime(date, "%Y-%m-%d")
                timestamp = int(_date.timestamp())
            
            except ValueError: 
                
                await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"`date` is invalid and must be in `YYYY-MM-DD` format.", bot = self.bot), ephemeral = True) # type: ignore
                return

        if not modify:
            
            status = await statuses.get_status(num, timestamp, match)
            
            if not status:
                
                await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Could not find this status with the provided arguments.", bot = self.bot), ephemeral = True) # type: ignore
                return
                
            text = status[2] # type: ignore
            emoji = content = None
            
            if text:
                emoji = text.split(':')[1]
                content = text.split(':')[2]
                
            await interaction.followup.send(embed = basic_embed(title = "Daily Statuses", description = f"### Daily Status #{status[0]}\n> - **Status Date**: <t:{status[1]}:D>\n> - **Status Text**: {content if content else ""}\n> - **Status Emoji**: {":" + emoji + ":" if emoji else ""}", bot = self.bot), ephemeral = True) # type: ignore
            
        elif modify:
            
            status = await statuses.get_status(num, timestamp, match)
            
            if not status:
                
                await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Could not find this status with the provided arguments.", bot = self.bot), ephemeral = True) # type: ignore
                return
            
            text = status[2] # type: ignore
            emoji = content = None
            
            if text:
                emoji = text.split(':')[1]
                content = text.split(':')[2]
                
            n = status[0]
            await statuses.update_status(n, f":{emoji}:" + modify)
            
            await interaction.followup.send(embed = basic_embed(title = "Daily Statuses", description = f"Status updated.", bot = self.bot), ephemeral = True) # type: ignore        
    
    # /restart
    @app_commands.command(name = "restart", description = "Restart the bot.")
    async def restart(self, interaction: discord.Interaction):
        
        pass
      
async def import_dates():
    
    timestamps = list(range(1681603200 + 86400, 1773705600 + (2 * 86400), 86400))
    
    for i, timestamp in enumerate(timestamps):
        
        await db.conn.execute(
                """
                UPDATE statuses
                SET date = ?
                WHERE number = ?
                """, ((timestamp, i + 1,)))
    
    await db.conn.commit()             