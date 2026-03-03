# cogs > __init__.py // @toblobs // 02.03.26

import os

import discord
import numpy

from dotenv import load_dotenv

DEFAULT_COLOR = discord.Color.from_rgb(183, 117, 219)

load_dotenv("secrets.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

