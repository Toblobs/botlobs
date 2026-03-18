# database > schema.py // @toblobs // 18.03.26

from .__init__ import *
import aiosqlite

from .dbio import db

async def create_tables():

    await db.conn.executescript( 
    """
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        xp INTEGER DEFAULT 0,
        level INTEGER DEFAULT 0,
        prestige INTEGER DEFAULT 0,
        intro_text TEXT,
        birthday TEXT,
        country TEXT
    );

    CREATE TABLE IF NOT EXISTS xp_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        channel_id INTEGER,
        timestamp INTEGER,
        xp_change INTEGER,
        source TEXT DEFAULT 'message',
        moderator_id INTEGER DEFAULT -1
    );

    CREATE TABLE IF NOT EXISTS multipliers ( 
        role_id INTEGER,
        channel_id INTEGER,
        multiplier REAL,
        PRIMARY KEY(role_id, channel_id)
    );

    CREATE TABLE IF NOT EXISTS reward_roles (
        level INTEGER,
        role_id INTEGER,
        keep INTEGER,
        sync INTEGER
    );

    CREATE TABLE IF NOT EXISTS statuses (
        number INTEGER PRIMARY KEY AUTOINCREMENT,
        date INTEGER,
        text TEXT
    );

    CREATE TABLE IF NOT EXISTS reminders (
        reminder_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        timestamp INTEGER,
        repeat TEXT,
        channel_id INTEGER,
        message TEXT
    );

    CREATE TABLE IF NOT EXISTS quotes (
        quote_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        message_id INTEGER,
        content TEXT,
        timestamp INTEGER
    );

    CREATE TABLE IF NOT EXISTS customs (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        tie_color TEXT
    );
    """)

    await db.conn.commit() 

async def create_indexes():

    await db.conn.executescript( 
    """
    CREATE INDEX IF NOT EXISTS idx_xp_time
    ON xp_log(timestamp);

    CREATE INDEX IF NOT EXISTS idx_xp_channel_time
    ON xp_log(channel_id, timestamp);

    CREATE INDEX IF NOT EXISTS idx_xp_user_time
    ON xp_log(user_id,timestamp);

    CREATE INDEX IF NOT EXISTS idx_users_xp
    ON users(xp DESC);
    """)

    await db.conn.commit() 