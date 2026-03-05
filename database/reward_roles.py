# database > reward_roles.py // @toblobs // 04.03.26

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