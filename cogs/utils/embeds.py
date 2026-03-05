# cogs > utils > embeds.py // @toblobs // 04.03.26

from __init__ import *

def basic_embed(title: str, description: str, bot: commands.Bot, thumbnail: str | None = None) -> discord.Embed:

    e = discord.Embed(title = title, description = description, color = DEFAULT_COLOR, timestamp = datetime.now())
    e.set_author(name = f"BotLobs", icon_url = bot.user.display_avatar.url) # type: ignore
    if thumbnail: e.set_thumbnail(url = thumbnail)
    
    return e
