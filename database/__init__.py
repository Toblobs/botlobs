# database > __init__.py // @toblobs // 07.03.26

import time
import re
from datetime import datetime
from dateutil import relativedelta


import os
import asyncio
import aiosqlite
from dotenv import load_dotenv

DATABASE_COMMIT_COOLDOWN = 30
DATABASE_PATH = r"C:\Users\Tobil\Documents\botlobs\database\data\botlobs.db"

XP_ENABLED = True

XP_MIN = 25
XP_MAX = 50

XP_COOLDOWN = 10

load_dotenv("secrets.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
