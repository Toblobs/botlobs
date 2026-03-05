# database > leaderboard.py // @toblobs // 05.03.26

from .__init__ import *

import time
from .dbio import db
from .xp import *
import discord

from typing import List

async def top_users(limit: int = 10):

    cur = await db.conn.execute("""
        SELECT user_id,xp,level
        FROM users
        ORDER BY xp DESC
        LIMIT ?
    """,(limit,))

    return await cur.fetchall()

async def leaderboard_page(page: int = 1):

    offset = page * 10

    cur = await db.conn.execute("""
        SELECT user_id,xp,level
        FROM users
        ORDER BY xp DESC
        LIMIT 10 OFFSET ?
    """,(offset,))

    return await cur.fetchall()

async def time_filtered_leaderboard_page(timestamp: int, page: int = 1):

    offset = page * 10

    cur = await db.conn.execute("""
        SELECT user_id, SUM(xp_change) as xp
        FROM xp_log
        WHERE timestamp > ?
        GROUP BY user_id
        ORDER BY xp DESC
        LIMIT 10 OFFSET ?
    """,(timestamp, offset,))

    return await cur.fetchall()

async def get_rank(member: discord.Member):

    cur = await db.conn.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE xp > (
            SELECT xp FROM users WHERE user_id=?
        )
    """,(member.id))

    return await cur.fetchone()

async def get_time_filtered_xp(timestamp: int, member: discord.Member):

    cur = await db.conn.execute("""
        SELECT user_id, xp, rank
        FROM (
            SELECT
                user_id,
                SUM(xp_change) AS xp
                RANK() OVER (ORDER BY SUM(xp_change) DESC) AS rank
            FROM xp_log
            WHERE timestamp > ?
            GROUP BY user_id
        )
        WHERE user_id = ?
    """,(timestamp,member.id))

    return await cur.fetchone() # in format: id | xp | rank

async def get_xp_logs(timestamp: int, members_ids: List[int]):

    if not members_ids:
        return [] 

    placeholders = ",".join("?" for _ in members_ids)

    query = f"""
        SELECT user_id, timestamp, xp_change
        FROM xp_log
        WHERE timestamp > ?
        AND user_id IN ({placeholders})
        ORDER BY timestamp
    """

    cur = await db.conn.execute(query, (timestamp, *members_ids))
    return await cur.fetchall() # in format: id | timestamp | xp_change
