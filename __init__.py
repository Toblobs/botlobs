# __init__.py // @toblobs // 18.03.26

import os
import numpy

from datetime import datetime, timezone
from dotenv import load_dotenv

import discord
from discord.ext import commands

DEFAULT_COLOR = discord.Color.from_rgb(183, 117, 219)

load_dotenv("secrets.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")
__version__ = os.getenv("VERSION")
