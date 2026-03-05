# database > __init__.py // @toblobs // 03.03.26

import time
import os
import asyncio
import aiosqlite
from dotenv import load_dotenv

DATABASE_COMMIT_COOLDOWN = 30
DATABASE_PATH = r"/home/toblobs/botlobs/database/data/botlobs.db"

XP_ENABLED = True

XP_MIN = 25
XP_MAX = 50

XP_COOLDOWN = 30

load_dotenv("secrets.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

