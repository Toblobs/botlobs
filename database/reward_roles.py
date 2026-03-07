# database > reward_roles.py // @toblobs // 07.03.26

from .__init__ import *

import time
import discord
from .dbio import db
from .xp import *

async def get_roles_for_level(level: int): 

    cur = await db.conn.execute("""
        SELECT level, role_id, keep, sync
        FROM reward_roles
        WHERE level <= ?
        ORDER BY level ASC
    """,(level,))

    return await cur.fetchall()

async def get_keepable_roles():

    cur = await db.conn.execute("""
        SELECT role_id
        FROM reward_roles
        WHERE keep=1
    """)

    rows = await cur.fetchall()
    return [r[0] for r in rows]
    
async def get_syncable_roles():

    cur = await db.conn.execute("""
        SELECT role_id
        FROM reward_roles
        WHERE sync=1
    """)

    rows = await cur.fetchall()
    return [r[0] for r in rows]

async def add_custom(role_id: int, user_id: int, tie_color: str):

    cur = await db.conn.execute("""
        INSERT INTO customs(id,user_id,tie_color)
        VALUES (?,?,?)
        ON CONFLICT(id)
        DO NOTHING
    """, (role_id, user_id, tie_color))

async def remove_custom(role_id: int):
    
    cur = await db.conn.execute("""
        DELETE FROM customs
        WHERE id=?
    """, (role_id,))

async def get_custom(role_id: int):

    cur = await db.conn.execute("""
        SELECT id, user_id, tie_color
        FROM customs
        WHERE id=?
    """, (role_id,))

    return await cur.fetchone()
    
async def get_all_customs():

    cur = await db.conn.execute("""
        SELECT id, user_id, tie_color
        FROM customs
        """)
    
    return await cur.fetchall() # format id | user_id | tie_color