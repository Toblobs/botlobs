# __init__.py // @toblobs // 07.03.26

__version__ = "0.1.2"

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

