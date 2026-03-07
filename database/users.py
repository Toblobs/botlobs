# database > users.py // @toblobs // 07.03.26

from .__init__ import *

import time
import aiosqlite
import discord
from discord.ext import commands
import numpy as np

from .dbio import db

async def get_user(user_id: int):

    cur = await db.conn.execute("""
        SELECT xp, level, prestige, intro_text, birthday, country
        FROM users
        WHERE user_id=?
    """,(user_id,))

    return await cur.fetchone()

async def set_user_intro(user_id: int, intro_text: str, birthday: int, country: str):
    
    await db.conn.execute("""
        UPDATE users
        SET intro_text = ?, 
        birthday = ?, 
        country = ?
        WHERE user_id = ?     
    """,(intro_text, birthday, country, user_id))
    
    await db.conn.commit()
    
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

