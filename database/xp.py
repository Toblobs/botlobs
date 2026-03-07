# database > xp.py // @toblobs // 07.03.26

from .__init__ import *

import time
import discord
from discord.ext import commands
import numpy as np

from .dbio import db
from .sync import sync_roles

async def log_message(user_id: int, channel_id: int, xp: int):

    ts = int(time.time())

    await db.conn.execute( 
        """
        INSERT INTO xp_log
        (user_id, channel_id, timestamp, xp_change, source, moderator_id)
        VALUES (?, ?, ?, ?, 'message', -1)
        """,
        (user_id, channel_id, ts, xp)
    )

    await db.conn.execute( 
        """
        INSERT INTO users(user_id, xp)
        VALUES(?, ?)
        ON CONFLICT(user_id)
        DO UPDATE SET xp = xp + ?
        """,
        (user_id, xp, xp)
    )

last_xp_time: dict[int, float] = {}

def xp_required(level: int):

    xp = (1.5 * level  ** 3) + (15 * level ** 2) + (150 * level)
    return round(xp/100) * 100

def level_from_xp(xp: int):

    level = 0

    while xp_required(level + 1) <= xp:
        level += 1
    
    return level

async def count_messages(channel_id: int | None = None, timestamp: int | None = None, user_id: int | None = None) -> int:

    query = "SELECT COUNT(*) FROM xp_log"

    filters = []
    params = []

    if channel_id is not None:
        filters.append("channel_id = ?")
        params.append(channel_id)
    
    if timestamp is not None:
        filters.append("timestamp > ?")
        params.append(timestamp)
    
    if user_id is not None:
        filters.append("user_id = ?")
        params.append(user_id)

    if filters:
        query += " WHERE " + " AND ".join(filters)
    
    cur = await db.conn.execute(query, params)
    result = await cur.fetchone()
    return result[0] if result else 0

async def get_roles_for_level(level):

    cur = await db.conn.execute("""
        SELECT role_id, keep, sync
        FROM reward_roles
        WHERE level <= ?
        ORDER BY level
    """,(level,))

    return await cur.fetchall()

async def get_syncable_roles():

    cur = await db.conn.execute("""
        SELECT role_id
        FROM reward_roles
        WHERE sync=1
    """)

    rows = await cur.fetchall()
    return [r[0] for r in rows]

async def role_multiplier(member) -> float:
    
    role_ids = [r.id for r in member.roles]

    cur = await db.conn.execute("""
        SELECT multiplier
        FROM multipliers
        WHERE role_id in ({})
    
    """.format(",".join("?"*len(role_ids))), role_ids)

    rows = await cur.fetchall()

    if not rows: return 1.0
    return max(r[0] for r in rows)

async def channel_multiplier(channel) -> float:
    
    channel_ids = [channel.id]
    if channel.category: channel_ids.append(channel.category.id)

    cur = await db.conn.execute("""
        SELECT multiplier
        FROM multipliers
        WHERE channel_id in ({})
    
    """.format(",".join("?"*len(channel_ids))), channel_ids)

    rows = await cur.fetchall()
    mult = 1.0

    for r in rows: mult *= r[0]
    return mult

async def set_xp(user_id, xp):

    level = level_from_xp(xp)

    await db.conn.execute("""
        INSERT INTO users(user_id,xp,level)
        VALUES(?,?,?)
        ON CONFLICT(user_id)
        DO UPDATE SET
        xp=?
        level=?
    """, (user_id, xp, level, xp, level))

async def level_up(member: discord.Member, current_xp: int, level: int, bot: commands.Bot):

    xp_cog = bot.get_cog("XPCommands")

    full_xp_to_next = xp_required(level = level + 1) - xp_required(level = level)
    xp_gained = current_xp - xp_required(level = level)
    xp_to_next = (full_xp_to_next )- xp_gained

    obtained_roles = (await sync_roles(member, level, bot))[0]

    await xp_cog.level_up_message(member = member, level = level, # type: ignore
    current_xp = current_xp, xp_gained = xp_gained, full_xp_to_next = full_xp_to_next,
    xp_to_next = xp_to_next, obtained_roles = obtained_roles)

def get_member_cooldown(member: discord.Member):

    now = time.time()
    last = last_xp_time.get(member.id)
    
    if last: return (now - last)
    else: return XP_COOLDOWN

async def get_member_highest_multiplier(member):
    
    role_ids = [r.id for r in member.roles]

    cur = await db.conn.execute("""
        SELECT role_id, multiplier
        FROM multipliers
        WHERE role_id in ({})
    
    """.format(",".join("?"*len(role_ids))), role_ids)

    rows = await cur.fetchall()

    if not rows: return (None, 1.0)
    return max(rows, key = lambda r: r[1])    
    
async def process_message(message: discord.Message, bot: commands.Bot):

    user_id = message.author.id
    now = time.time()

    # Check and update cooldown
    if get_member_cooldown(message.author) < XP_COOLDOWN: return # type: ignore

    last_xp_time[user_id] = now

    # Calculate XP
    base_xp = np.random.randint(low = XP_MIN, high = XP_MAX + 1)
    role_mult = await role_multiplier(message.author)
    channel_mult = await channel_multiplier(message.channel)

    if role_mult == 0 or channel_mult == 0:

        #print(f"{message.author.name} has a role or channel multiplier of 0")

        return

    xp_gain = int(base_xp * role_mult * channel_mult)

    #print(f"xp gain calculated as {xp_gain} ({[base_xp, role_mult, channel_mult]}) for {message.author.name}")

    # Get current XP
    cur = await db.conn.execute("""
        SELECT xp, level
        FROM users
        WHERE user_id=?
    """,(user_id,))

    row = await cur.fetchone()

    if row: old_xp, old_level = row 
    else: old_xp = old_level = 0

    new_xp = old_xp + xp_gain
    new_level = level_from_xp(new_xp)

    # Insert into xp_log and user tables
    ts = int(now)

    await db.conn.execute("""
        INSERT INTO xp_log
        (id,user_id,channel_id,timestamp,xp_change,source)
        VALUES (?,?,?,?,?,'message')
    """, (message.id, user_id, message.channel.id, ts, xp_gain))

    await db.conn.execute("""
        INSERT INTO users(user_id,xp,level)
        VALUES(?,?,?)
        ON CONFLICT(user_id)
        DO UPDATE SET
            xp=?,
            level=?
    """, (user_id, new_xp, new_level, new_xp, new_level))

    if new_level > old_level:

        await level_up(message.author, new_xp, new_level, bot) # type: ignore

async def import_xp():

    with open(r"C:\Users\Tobil\Documents\botlobs\database\frozen-xp.txt") as f:

        for line in f:

            if '-' not in line:
                continue

            user_id, xp = line.split("-")
            user_id = int(user_id.strip())
            xp = int(xp.strip())
            level = level_from_xp(xp)

            await db.conn.execute(
                """
                INSERT INTO users(user_id, xp, level)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id)
                DO UPDATE SET
                    xp = excluded.xp,
                    level = excluded.level
                """,
                (user_id,xp,level)
            )
    
    await db.conn.commit()

