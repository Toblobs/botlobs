# main.py // @toblobs // 02.03.26

from __init__ import *
from cogs.general import GeneralCommands

intents = discord.Intents.all()
intents.typing = False

flags = discord.ApplicationFlags()

bot = commands.Bot(command_prefix = '/', intents = intents)

@bot.event
async def on_ready():

    await bot.add_cog(GeneralCommands(bot))
    await bot.tree.sync()

bot.run(BOT_TOKEN) # type: ignore


