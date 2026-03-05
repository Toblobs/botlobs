# database > dbio.py // @toblobs // 04.03.26

from .__init__ import *

import aiosqlite

class Database:

    def __init__(self):

        self.conn: aiosqlite.Connection

    async def connect(self):

        self.conn = await aiosqlite.connect(DATABASE_PATH)

        await self.conn.execute("PRAGMA journal_mode=WAL;")
        await self.conn.execute("PRAGMA synchronous=NORMAL;")

        await self.conn.commit()
    
    async def close(self):

        await self.conn.close() 

db = Database()

async def commit_loop():

    #await asyncio.sleep(10) # startup sleep

    while True:

        if db.conn: await db.conn.commit()
        await asyncio.sleep(DATABASE_COMMIT_COOLDOWN)

async def period_count(channel_id = None, period: str = "daily"):

    time_periods = {"daily": 86400, "weekly": 604800, "monthly": 2592000}

    if period not in list(time_periods.keys()): return None

    now = int(time.time())
    seconds = now - time_periods[period]

    if channel_id:

        cur = await db.conn.execute(
            """
            SELECT COUNT(*)
            FROM xp_log
            WHERE timestamp > ?
            AND channel_id = ?
            """,
            (seconds, channel_id)
        )

    else:

        cur = await db.conn.execute(
            """
            SELECT COUNT(*)
            FROM xp_log
            WHERE timestamp > ?
            """,
            (seconds,)
        )
    return (await cur.fetchone())[0] # type: ignore
