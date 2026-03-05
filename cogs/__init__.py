# cogs > __init__.py // @toblobs // 04.03.26

import os

import discord
from discord.ext import commands
import numpy

from dotenv import load_dotenv

DEFAULT_COLOR = discord.Color.from_rgb(183, 117, 219)

load_dotenv("secrets.env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

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