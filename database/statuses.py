# database > statuses.py // @toblobs // 18.03.26

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

async def add_status(date: int, number: int, text: str):
    
    cur = await db.conn.execute("""
        INSERT INTO statuses(number, date, text)                        
        VALUES(?, ?, ?)
        ON CONFLICT(number)
        DO NOTHING
        """, (date, number, text,))
    
    return cur.lastrowid
    
async def delete_status(number: int):
    
    cur = await db.conn.execute("""
        DELETE FROM statuses
        WHERE number = ?
        """, (number,))

async def get_status(number: int | None = None, date: int | None = None, match: str | None = None):
    
    if number == date == match == None:
        
        raise ValueError("Expecting one of member or date or match")
    
    if number:
        
        cur = await db.conn.execute("""
            SELECT * FROM statuses
            WHERE number = ?                 
            """, (number,))
    
    elif date:
        
        cur = await db.conn.execute("""
            SELECT * FROM statuses
            WHERE date = ?              
            """, (date,))
    
    elif match:
        
        cur = await db.conn.execute("""
            SELECT * FROM statuses
            WHERE text LIKE LOWER(?)                      
            """, (f"%{match}%",))

    return (await cur.fetchone()) # type: ignore

async def update_status(number: int, text: str):
    
    cur = await db.conn.execute("""
        UPDATE statuses
        SET text = ?
        WHERE number = ?                 
        """, (text, number))
    
    await db.conn.commit()
    
async def get_all_statuses():
    
    cur = await db.conn.execute("""
        SELECT * FROM statuses
    """)
    
    return (await cur.fetchall())