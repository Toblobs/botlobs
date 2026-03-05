# database > users.py // @toblobs // 04.03.26

from .__init__ import *

import time
import aiosqlite
import discord
from discord.ext import commands
import numpy as np

from .dbio import db

async def get_user(user_id: int):

    cur = await db.conn.execute("""
        SELECT xp, level, prestige
        FROM users
        WHERE user_id=?
    """,(user_id,))

    return await cur.fetchone()

async def ensure_user(user_id: int):

    await db.conn.execute("""
        INSERT INTO users(user_id)
        VALUES(?)
        ON CONFLICT(user_id)
        DO NOTHING
    """)

async def get_user_level(user_id: int):

    cur = await db.conn.execute("""
        SELECT level
        FROM users
        WHERE user_id=?
    """,(user_id,))

    row = await cur.fetchone()
    if row: return row[0]

    return 0

