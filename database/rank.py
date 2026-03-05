# database > rank.py // @toblobs // 05.03.26

from .__init__ import *

import time
from .dbio import db

async def get_rank(user_id):

    cur = await db.conn.execute("""
        SELECT xp
        FROM users
        WHERE user_id=?
    """,(user_id,))

    xp = (await cur.fetchone())[0] # type: ignore
    
    cur = await db.conn.execute("""
        SELECT Count(*)
        FROM users
        WHERE xp > ?    
    """,(xp,))

    higher = (await cur.fetchone())[0] # type: ignore

    return higher + 1

async def get_time_filtered_rank(timestamp, user_id):

    cur = await db.conn.execute("""
        SELECT rank
        FROM (
            SELECT
                user_id,
                RANK() OVER (ORDER BY SUM(xp_change) DESC) AS rank
            FROM xp_log
            WHERE timestamp > ?
            GROUP BY user_id
        ) ranked
        WHERE user_id = ?
    """, (timestamp, user_id))

    result = await cur.fetchone()
    if result is None: return None
    return result[0]

async def total_users():

    cur = await db.conn.execute("""
        SELECT Count(*)
        FROM users
    """)

    return (await cur.fetchone())[0] # type: ignore

async def xp_period(user_id, period):

    time_periods = {"daily": 86400, "weekly": 604800, "monthly": 2592000}

    if period not in list(time_periods.keys()): return

    t = time.time() - time_periods[period]

    cur = await db.conn.execute("""
        SELECT SUM(xp_change)
        FROM xp_log
        WHERE user_id=?
        AND timestamp>?
        AND source='message'
    """,(user_id,t))

    r = await cur.fetchone()
    return r[0] or 0 # type: ignore



