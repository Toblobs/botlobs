# cogs > __init__.py // @toblobs // 10.03.26

import os
import io
import re

import discord
from datetime import datetime
from dateutil.relativedelta import relativedelta

from discord.ext import commands
import numpy

from dotenv import load_dotenv

from .utils.embeds import basic_embed
from PIL import Image

DEFAULT_COLOR = discord.Color.from_rgb(183, 117, 219)

load_dotenv("secrets.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

BOT_ID = 1478062732392661164
BOT_LOGS_CHANNEL = 1140063993034199091

ASSET_CHANNEL_ID = 1479089948215742464

async def upload_asset(bot: commands.Bot, file: discord.File):

    channel = bot.get_channel(ASSET_CHANNEL_ID)
    msg = await channel.send(file = file) # type: ignore

    attachment = msg.attachments[0]
    return attachment.url

def get_top_colored_role(member: discord.Member):

    top_colored_role = None

    for role in reversed(member.roles):

        if role.color != discord.Color.default():
            top_colored_role = role
            break

    return top_colored_role

async def get_icon_binary(icon) -> bytes | None:

    if icon:

        if icon.size > 256 * 1024:
            raise ValueError("Image provided is too large (max `256` kilobytes).")

        img = Image.open(io.BytesIO(await icon.read())) 

        if img.size != (64, 64):
            raise ValueError(f"Image provided must be `64`x`64` pixels.")
        
        with io.BytesIO() as image_binary:

            img.save(image_binary, format = "PNG")
            image_binary.seek(0)
            return image_binary.getvalue()

    else:

        return None
    
def parse_time_string(time_str: str) -> relativedelta:
         
    now = datetime.now()
    
    kwargs = {"years": 0, "months": 0, "weeks": 0, "days": 0, "hours": 0, "minutes": 0, "seconds": 0}
    TIME_PATTERN = re.compile(r"(\d+)(y|mo|w|d|h|m|s)")
    
    matches = TIME_PATTERN.findall(time_str.lower())
    if not matches: raise ValueError("Invalid time format. Examples: `1h30m`, `2d`, `3mo4w`")
    
    for value, unit in matches:
        value = int(value)
        
        if unit == "y": kwargs["years"] += value
        elif unit == "mo": kwargs["months"] += value
        elif unit == "w": kwargs["weeks"] += value
        elif unit == "d": kwargs["days"] += value
        elif unit == "h": kwargs["hours"] += value
        elif unit == "m": kwargs["minutes"] += value
        elif unit == "s": kwargs["seconds"] += value
    
    return relativedelta(**kwargs) # type: ignore