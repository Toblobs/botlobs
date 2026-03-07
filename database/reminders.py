# database > reminders.py // @toblobs // 07.03.26

from .__init__ import *

import time
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

async def add_reminder(user_id: int, timestamp: int, channel_id: int, message: Optional[str], repeat: Optional[str]):
    
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
    
    now = int(time.time())
    
    cur = await db.conn.execute("""
        SELECT * FROM reminders
        WHERE timestamp <= ?                            
    """, (now,))
    
    return (await cur.fetchall())

async def get_next_reminder(): 
    
    now = int(time.time())
    
    cur = await db.conn.execute("""
        SELECT * FROM REMINDERS
        ORDER BY timestamp
        LIMIT 1              
    """)
    
    return (await cur.fetchone())

async def trigger_reminder(bot: commands.Bot, row):
    
    if (await get_reminder(int(row[0]))):
        
        print(await get_reminder(int(row[0])))
        print('a')
        
        user = bot.get_user(int(row[1]))
        channel: discord.TextChannel = bot.get_channel(int(row[4])) # type: ignore

        if channel and user: await channel.send(f"{user.mention}", embed = basic_embed(title = "Reminder", description = f"Reminder triggered for {user.mention}\n> **Message**: {row[5]} \n> - **Reminder ID**: `{row[0]}`", bot = bot, thumbnail = f"https://twemoji.maxcdn.com/v/latest/72x72/{ord("⏰"):x}.png")) 
        
        if bool(row[3]):
            new_timestamp = int((datetime.now() + parse_time_string(row[3])).timestamp()) # type: ignore
            await update_reminder_timestamp(int(row[0]), new_timestamp)
        
        else:
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