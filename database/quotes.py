# database > quotes.py // @toblobs // 18.03.26

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

async def add_quote(user_id: int, message_id: int, content: str, timestamp: int):
    
    cur = await db.conn.execute("""
        INSERT INTO quotes(user_id, message_id, content, timestamp)
        VALUES(?,?,?,?)
    """, (user_id, message_id, content, timestamp))

    return cur.lastrowid

async def delete_quote(quote_id: int):
    
    cur = await db.conn.execute("""
        DELETE FROM quotes
        WHERE quote_id = ?               
    """, (quote_id,))
    
async def get_quote(quote_id: int):

    cur = await db.conn.execute("""
        SELECT * FROM quotes
        WHERE quote_id = ?         
    """, (quote_id,))
    
    return (await cur.fetchone())

async def get_all_quotes():
    
    cur = await db.conn.execute("""
        SELECT * FROM quotes         
    """)
    
    return (await cur.fetchall())

async def get_member_quotes(user_id: int):
    
    cur = await db.conn.execute("""
        SELECT * FROM quotes
        WHERE user_id = ?         
    """, (user_id,))
    
    return (await cur.fetchall())