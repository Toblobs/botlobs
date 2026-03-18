# database > reminders.py // @toblobs // 18.03.26

from .__init__ import *

import time
import random
import discord
from discord.ext import commands

from datetime import datetime
from dateutil.relativedelta import relativedelta

import numpy as np

from .dbio import db
from typing import Optional, List

# Duplicate code, get rid of somehow

DEFAULT_COLOR = discord.Color.from_rgb(183, 117, 219)

def basic_embed(title: str, description: str, bot: commands.Bot, thumbnail: str | None = None) -> discord.Embed:

    e = discord.Embed(title = title, description = description, color = DEFAULT_COLOR, timestamp = datetime.now())
    e.set_author(name = f"BotLobs", icon_url = bot.user.display_avatar.url) # type: ignore
    if thumbnail: e.set_thumbnail(url = thumbnail)
    
    return e

def parse_time_string(time_str: str) -> int:
         
    now = datetime.now()
    
    kwargs = {"years": 0, "months": 0, "weeks": 0, "days": 0, "hours": 0, "minutes": 0, "seconds": 0}
    TIME_PATTERN = re.compile(r"(\d+)(y|mo|w|d|h|m|s)")
    
    matches = TIME_PATTERN.findall(time_str.lower())
    if not matches: raise ValueError("Invalid time format. Examples: `1h30m`, `2d`, `3mo4w`")
    
    for value, unit in matches:
        value = int(value)
        
        if unit == "y": kwargs["years"] += value
        elif unit == "mo": kwargs["months"] += value
        elif unit == "w": kwargs["weeks"] += value
        elif unit == "d": kwargs["days"] += value
        elif unit == "h": kwargs["hours"] += value
        elif unit == "m": kwargs["minutes"] += value
        elif unit == "s": kwargs["seconds"] += value
    
    return relativedelta(**kwargs) # type: ignore

# All reminders add and delete instantly

async def add_reminder(user_id: int, timestamp: int, channel_id: int, message: Optional[str] = None, repeat: Optional[str] = None):
    
    cur = await db.conn.execute("""
        INSERT INTO reminders(user_id, timestamp, channel_id, message, repeat)
        VALUES (?,?,?,?,?)                                  
    """, (user_id, timestamp, channel_id, message, repeat))
    
    await db.conn.commit()
    
    return cur.lastrowid
    
async def get_user_reminder(user_id: int, repeating_only = False):
    
    query = """
            SELECT *
            FROM reminders
            WHERE user_id = ?                           
            """
    
    if repeating_only: query += "\nAND repeat is NOT NULL"
    
    cur = await db.conn.execute(query, (user_id,))
    return (await cur.fetchall())

async def get_reminder(reminder_id: int):
    
    cur = await db.conn.execute("""
        SELECT *
        FROM reminders
        WHERE reminder_id = ?                           
    """, (reminder_id,))
    
    return (await cur.fetchone())

async def update_reminder_timestamp(reminder_id: int, timestamp: int):
    
    cur = await db.conn.execute("""
        UPDATE reminders
        SET timestamp = ?
        WHERE reminder_id = ?
    """, (timestamp, reminder_id))
    
    await db.conn.commit()
    
async def delete_reminder(reminder_id: int):

    cur = await db.conn.execute("""
        DELETE FROM reminders
        WHERE reminder_id = ?
    """, (reminder_id,))
    
    await db.conn.commit()
    
async def get_due_reminders():
    
    now = int(datetime.now().timestamp())
    
    cur = await db.conn.execute("""
        SELECT * FROM reminders
        WHERE timestamp > ?                            
    """, (now,))
    
    return (await cur.fetchall())

async def get_next_reminder(): 

    cur = await db.conn.execute("""
        SELECT * FROM REMINDERS
        ORDER BY timestamp
        LIMIT 1              
    """)
    
    return (await cur.fetchone())

async def trigger_reminder(bot: commands.Bot, row):
    
    if (await get_reminder(int(row[0]))):
        
        if int(row[1]) != BOT_ID:
        
            user = bot.get_user(int(row[1]))
            channel: discord.TextChannel = bot.get_channel(int(row[4])) # type: ignore

            if channel and user: await channel.send(f"{user.mention}", embed = basic_embed(title = "Reminder", description = f"Reminder triggered for {user.mention}\n> **Message**: {row[5]} \n> - **Reminder ID**: `{row[0]}`", bot = bot, thumbnail = f"https://twemoji.maxcdn.com/v/latest/72x72/{ord("⏰"):x}.png")) 
            
            if bool(row[3]):
                new_timestamp = int((datetime.now() + parse_time_string(row[3])).timestamp()) # type: ignore
                await update_reminder_timestamp(int(row[0]), new_timestamp)
            
            else:
                await delete_reminder(int(row[0]))
        
        else: # special bot reminder to do something

            reminder_type = str(row[5]).split(':')[0]
            reminder_info = str(row[5]).split(':')[1]
            
            match reminder_type:
                
                case "cooldown":
                    
                    await delete_reminder(int(row[0]))
                
                case "unmute":
                    
                    guild = bot.get_guild(int(GUILD_ID)) # type: ignore
                    user_id = int(reminder_info)

                    try:   
                        
                        muted_role = guild.get_role(1140287361352204339) # type: ignore 
                        solitary_role = guild.get_role(1140287435809497108) # type: ignore

                        member = guild.get_member(user_id) # type: ignore
                        
                        if muted_role in member.roles: await member.remove_roles(muted_role) # type: ignore
                        if solitary_role in member.roles: await member.remove_roles(solitary_role) # type: ignore
                    
                    except Exception: pass

                    await delete_reminder(int(row[0]))

                case "unban":
                    
                    guild = bot.get_guild(int(GUILD_ID)) # type: ignore
                    user_id = int(reminder_info)
                    
                    try: await guild.unban(await bot.fetch_user(user_id), reason = "Temporary ban expired") # type: ignore
                    except Exception: pass
                    
                    await delete_reminder(int(row[0]))
                    
                case "birthday":
                    
                    new_timestamp = int((datetime.now() + parse_time_string(row[3])).timestamp()) # type: ignore
                    await update_reminder_timestamp(int(row[0]), new_timestamp)
                
                case "giveaway":
                    
                    guild = bot.get_guild(int(GUILD_ID)) # type: ignore
                    
                    role_id = int(str(row[5]).split(':')[2])
                    winner_amount = int(str(row[5]).split(':')[3])
                    
                    events_channel: discord.TextChannel = guild.get_channel(1140054643729252422) # type: ignore
                    message = await events_channel.fetch_message(int(reminder_info))
                    
                    role = None 
                    if role_id != -1: role = guild.get_role(role_id) # type: ignore

                    eligible = []
                    
                    async for member in guild.fetch_members(limit = None): # type: ignore
                        if not role: eligible.append(member)
                        elif role in member.roles: eligible.append(member)
                        else: continue

                    winners = []
                    for r in range(winner_amount): winners.append(random.choice(eligible))
                    
                    await message.reply(embed = basic_embed(title = "Giveaway: Results", description = f"The winner(s) of this giveaway are: {" ".join(w.mention for w in winners)}", bot = bot, thumbnail = f"https://twemoji.maxcdn.com/v/latest/72x72/{ord("🎆"):x}.png"))
                    
                    await delete_reminder(int(row[0]))
                    
                case "unlock":
                    
                    guild = bot.get_guild(int(GUILD_ID)) # type: ignore
                    locked_channel: discord.TextChannel = guild.get_channel(int(reminder_info)) # type: ignore
                    
                    everyone = guild.default_role # type: ignore
                    overwrite = locked_channel.overwrites_for(everyone)
                    overwrite.send_messages = None
                    overwrite.add_reactions = None
                    
                    await locked_channel.set_permissions(everyone, overwrite = overwrite)
                                        
                    # copypasted code, remove
                    JR_MOD_ROLE = 1139119456862339082
                    MOD_ROLE = 1139119339161784330
                    ADMIN_ROLE = 1139119232710344784
                    TOBLOBS_ROLE = 1139118721022046289

                    staff = [JR_MOD_ROLE, MOD_ROLE, ADMIN_ROLE, TOBLOBS_ROLE]

                    for mod_role in [guild.get_role(s) for s in staff]: # type: ignore
                        mod_overwrite = locked_channel.overwrites_for(mod_role) # type: ignore
                        mod_overwrite.send_messages = mod_overwrite.add_reactions = None
                        await locked_channel.set_permissions(mod_role, overwrite = mod_overwrite) # type: ignore
                    
                    await locked_channel.send(embed = basic_embed(title = "Channel Unlocked", description = "🔓 Channel unlocked.", bot = bot))
                    
                    await delete_reminder(int(row[0]))
                
                case "tierlistexpire":
                    
                    guild = bot.get_guild(int(GUILD_ID)) # type: ignore
                    member_id = int(reminder_info) # type: ignore
                    tier_channel = bot.get_channel(int(str(row[5]).split(':')[2]))
                    
                    fun_cog = bot.get_cog("FunCommands")
                    if member_id in fun_cog.live_tierlists.keys(): # type: ignore
                        del fun_cog.live_tierlists[member_id] # type: ignore
                        
                    await tier_channel.send(embed = basic_embed(title = "Tierlist Generator", description = f"Live tierlist ended.", bot = bot)) # type: ignore
                    
                    await delete_reminder(int(row[0]))
                                   
                case "event":
                    
                    guild = bot.get_guild(int(GUILD_ID)) # type: ignore
                    member = await bot.fetch_user(int(reminder_info)) # type: ignore
                    
                    #blob_role = guild.get_role(1139122746199134249) # type: ignore
                
                    try: event_thread = guild.get_channel_or_thread(int(str(row[5]).split(':')[4])) # type: ignore
                    except: event_thread = None 
                    
                    start = int(str(row[5]).split(':')[2])
                    end = int(str(row[5]).split(':')[3])
                    
                    if event_thread: await event_thread.send(content = f"", embed = basic_embed(title = "Event", description = f"An event hosted by {member.mention} is about to begin!\n> - **Event Start Time**: <t:{start}:F> (<t:{start}:R>)\n> - **Event End Time**: <t:{end}:F> (<t:{end}:R>)", bot = bot), allowed_mentions = discord.AllowedMentions(roles = True, everyone = True)) # type: ignore

                    await delete_reminder(int(row[0]))
                    
async def reminder_scheduler(bot: commands.Bot, wakeup: asyncio.Event):

    await bot.wait_until_ready()
    
    while not bot.is_closed():
        
        row = (await get_next_reminder())
        
        if row is None:
            
            wakeup.clear()
            await wakeup.wait()
            continue
            
        now = datetime.now()
        wait_time = (datetime.fromtimestamp(row[2]) - now).seconds # type: ignore
            
        if wait_time > 0: 
            
            try:
                
                wakeup.clear()
                await asyncio.wait_for(wakeup.wait(), timeout = wait_time)
                
                # woke up early due to new remidner
                continue
                
            except asyncio.TimeoutError:
                
                # reminder time reached
                pass
                
        await trigger_reminder(bot, row)