# cogs > tobs_commands.py // @toblobs // 21.03.26

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

from cogs.general_commands import send_about, send_introduction
from cogs.utils.emoji import *

class TobsCommands(commands.Cog):
    
    def __init__(self, bot: commands.Bot, wakeup: asyncio.Event, views):
        
        self.bot = bot
        self.wakeup = wakeup
        self.intro_view = views[0]
        self.reaction_views = [views[1], views[2], views[3], views[4], views[5]]
        
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
    @app_commands.describe(send_embeds = "Send the startup embeds in relevant channels.")
    async def restart(self, interaction: discord.Interaction, send_embeds: bool = True):
        
        if not toblobs_role in interaction.user.roles: # type: ignore
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"This command is reserved for {toblobs_role.mention}.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
        
        if send_embeds:
            
            await interaction.response.defer()
            
            guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
            metrics_channel = guild.get_channel(METRICS_CHANNEL) # type: ignore
            
            e = basic_embed(title = "Set Your Introduction",
                            description = "Welcome to the server!\nThis is where you can set your introduction (you can also use `/introduce` manually). In the form, add your:\n> - **About Me** with some basic info about yourself.\n> - **Birthdate** in the format (DD-MM), like `24-07`.\n> - **Country** being a Unicode country emoji, check out [Emojipedia](https://emojipedia.org/flag-united-kingdom) as an example.\nTo set the introduction, just click on the button below.",
                            bot = self.bot
            )
            
            await metrics_channel.send(content = "", file = discord.File(BANNER_FOLDER + r"\introductions-banner-wide.png")) # type: ignore     
            await metrics_channel.send(embed = e, view = self.intro_view) # type: ignore
            
            await metrics_channel.send(content = "", file = discord.File(BANNER_FOLDER + r"\reaction-roles-banner-wide.png")) # type: ignore     
            
            misc_channel = guild.get_channel(1140032670001275000) # type: ignore
            events_channel = guild.get_channel(1140054643729252422) # type: ignore
            
            misc_role = guild.get_role(1154296386469232693) # type: ignore
            event_role = guild.get_role(1154296321897926676) # type: ignore
            
            shades_role = guild.get_role(SHADES_ROLE) # type: ignore
            
            red_tie_role = guild.get_role(1140058151127887893) # type: ignore
            tangerina_role = guild.get_role(1140058044215066734) # type: ignore
            scottish_xanadu_role = guild.get_role(1140057941010022451) # type: ignore
            
            shades_plus_role = guild.get_role(SHADES_PLUS_ROLE) # type: ignore
            
            saffron_shades_role = guild.get_role(1237465948055933059) # type: ignore
            tealoblobs_role = guild.get_role(1237465819450179674) # type: ignore
            carmine_cuffs_role = guild.get_role(1237465605230035056) # type: ignore
            
            shades_plus_plus_role = guild.get_role(SHADES_PLUS_PLUS_ROLE) # type: ignore
            
            tobluebs_role = guild.get_role(1237473082923286528) # type: ignore
            blossom_blitz_role = guild.get_role(1237474170624016527) # type: ignore
            celadon_cultist_role = guild.get_role(1237474304229113908) # type: ignore
            
            e_1 = basic_embed(title = "Announcements Roles",
                            description = f"Press the {get_emoji("miscannouncements")} button for {misc_role.mention} in {misc_channel.mention} about minor pieces of news or achievements by server members.\n\nPress the {get_emoji("eventannouncements")} button for {event_role.mention} in {events_channel.mention} for keeping up to date with official server events and giveaways.", # type: ignore
                            bot = self.bot
            )
            
            e_2 = basic_embed(title = "Topical Roles",
                            description = f"Press the following buttons to be pinged for a certain topic/niche:\n> - {get_emoji("videogames")} | **Video Games**\n> - {get_emoji("algodoo")} | **Algodoo**\n> - {get_emoji("artandcreatives")} | **Art and Creatives**\n> - {get_emoji("music")} | **Music**\n> - {get_emoji("writingandbooks")} | **Writing and Books**\n> - {get_emoji("sports")} | **Sports**\n> - {get_emoji("pollnotifs")} | **Poll Notifications**\n ", # type: ignore
                            bot = self.bot
            ) 
            
            e_3 = basic_embed(title = "Shades (Level 25) Roles",
                            description = f"Press the following buttons to assign or swap your {shades_role.mention} {get_emoji("shades")} level up role:\n> - {get_emoji("redtie")} | {red_tie_role.mention}\n> - {get_emoji("tangerina")} | {tangerina_role.mention}\n> - {get_emoji("scottishxanadu")} | {scottish_xanadu_role.mention}", # type: ignore
                            bot = self.bot
            )
            
            e_4 = basic_embed(title = "Shades+ (Level 40) Roles",
                            description = f"Press the following buttons to assign or swap your {shades_plus_role.mention} {get_emoji("shadesplus")} level up role:\n> - {get_emoji("saffronshades")} | {saffron_shades_role.mention}\n> - {get_emoji("tealoblobs")} | {tealoblobs_role.mention}\n> - {get_emoji("carminecuffs")} | {carmine_cuffs_role.mention}", # type: ignore
                            bot = self.bot
            )
            
            e_5 = basic_embed(title = "Shades++ (Level 55) Roles",
                            description = f"Press the following buttons to assign or swap your {shades_plus_plus_role.mention} {get_emoji("shadesplusplus")} level up role:\n> - {get_emoji("tobluebs")} | {tobluebs_role.mention}\n> - {get_emoji("blossomblitz")} | {blossom_blitz_role.mention}\n> - {get_emoji("celadoncultist")} | {celadon_cultist_role.mention}", # type: ignore
                            bot = self.bot
            )
            
            for i, e in enumerate([e_1, e_2, e_3, e_4, e_5]):
                
                view = self.reaction_views[i]
                await metrics_channel.send(embed = e, view = view) # type: ignore

            #about_me_file = discord.File(BANNER_FOLDER + r"\about-banner-wide.png")
            #await metrics_channel.send(content = "", file = await upload_asset(self.bot, about_me_file)) # type: ignore     
            
            #await send_about(bot = self.bot, guild = guild, channel = metrics_channel)
            
            # ---
            await interaction.followup.send(embed = basic_embed(title = "Reset", description = f"Bot reset.", bot = self.bot), ephemeral = True) # type: ignore        
    
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