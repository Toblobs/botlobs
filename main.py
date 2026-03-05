# main.py // @toblobs // 05.03.26

from __init__ import *
from cogs.general_commands import GeneralCommands
from cogs.xp_commands import XPCommands

from database import XP_ENABLED, dbio, leaderboard, rank, reward_roles, schema, sync, users, xp
intents = discord.Intents.all()
intents.typing = False

#flags = discord.ApplicationFlags()

bot = commands.Bot(command_prefix = '/', intents = intents)

@bot.event
async def on_message(message):

    # Ignore other bots and commands
    if message.author.bot or message.content.startswith("/"):
        return

    # Log message

    # Deal with XP
    if not XP_ENABLED:
        return
    
    await xp.process_message(message, bot)

@bot.event
async def on_ready():

    # Add cogs
    await bot.add_cog(GeneralCommands(bot))
    await bot.add_cog(XPCommands(bot))

    # Sync tree
    await bot.tree.sync()

    print("[!] Connected to Discord")

async def main():

    # Start DB
    await dbio.db.connect()

    await schema.create_tables()
    await schema.create_indexes()
    
    print("[!] Connected to Database")

    #await xp.import_xp() # for testing

    asyncio.create_task(dbio.commit_loop())

    # Start bot
    async with bot:
        
        if BOT_TOKEN: await bot.start(BOT_TOKEN)


import asyncio
asyncio.run(main())
