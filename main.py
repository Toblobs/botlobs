# main.py // @toblobs // 21.03.26

from __init__ import *

import traceback
import asyncio

from cogs.passives import Automation, IntroView, ReactionView

from cogs.general_commands import GeneralCommands
from cogs.xp_commands import XPCommands
from cogs.staff_commands import StaffCommands
from cogs.fun_commands import FunCommands
from cogs.tobs_commands import TobsCommands, import_dates

from cogs.utils.embeds import basic_embed
from database import XP_ENABLED, dbio, schema, xp, reminders, users
intents = discord.Intents.all()
intents.typing = False

import logging
logging.basicConfig(level=logging.INFO)

bot = commands.Bot(command_prefix = '/', intents = intents)


# ----
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
async def on_member_join(member: discord.Member):
    
    # Add to DB if not present
    try: await users.get_user(member.id)
    except: await users.add_user(member.id)    
        
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: discord.app_commands.AppCommandError):
    
    traceback.print_exception(type(error), error, error.__traceback__)
    guild = bot.get_guild(int(GUILD_ID)) # type: ignore
    toblobs = guild.get_role(1139118721022046289) # type: ignore
    
    thumbnail_link = f"https://twemoji.maxcdn.com/v/latest/72x72/{ord("❗"):x}.png"
    
    try:
        
        if interaction.response.is_done():
            await interaction.followup.send(f"{toblobs.mention}", embed = basic_embed(title = "Error Encountered!", description = f"⚠️ An error occurred, {toblobs.mention} will check logs when possible.", bot = bot, thumbnail = thumbnail_link), allowed_mentions = discord.AllowedMentions(roles = True, users = True)) # type: ignore
        
        else:
            await interaction.response.send_message(f"{toblobs.mention}", embed = basic_embed(title = "Error Encountered!", description = f"⚠️ An error occurred, {toblobs.mention} will check logs when possible.", bot = bot, thumbnail = thumbnail_link), allowed_mentions = discord.AllowedMentions(roles = True, users = True)) # type: ignore
    
    except: 
        
        pass

wakeup = asyncio.Event()

@bot.event
async def on_ready():
    
    global wakeup

    # Add persistent views
    intro_view = IntroView(bot, wakeup)
    bot.add_view(intro_view)
    
    reaction_views = [ReactionView(bot, ["miscannouncements", "eventannouncements"]),
                      ReactionView(bot, ["videogames", "algodoo", "artandcreatives", "music", "writingandbooks", "sports", "pollnotifs"]),
                      ReactionView(bot, ["redtie", "tangerina", "scottishxanadu"]),
                      ReactionView(bot, ["saffronshades", "tealoblobs", "carminecuffs"]),
                      ReactionView(bot, ["tobluebs", "blossomblitz", "celadoncultist"])
    ]    
    
    for r in reaction_views: bot.add_view(r)
    
    # Add cogs
    await bot.add_cog(Automation(bot, wakeup))
    
    await bot.add_cog(GeneralCommands(bot, wakeup))
    await bot.add_cog(XPCommands(bot))
    await bot.add_cog(StaffCommands(bot, wakeup))
    await bot.add_cog(FunCommands(bot, wakeup))
    await bot.add_cog(TobsCommands(bot, wakeup, [intro_view] + reaction_views))

    # Sync tree
    await bot.tree.sync()
    print("[!] Connected to Discord")

async def main():
    
    global wakeup

    # Start DB
    await dbio.db.connect()

    await schema.create_tables()
    await schema.create_indexes()
    
    print("[!] Connected to Database")

    #await import_dates()

    asyncio.create_task(dbio.commit_loop())
    
    asyncio.create_task(reminders.reminder_scheduler(bot, wakeup))

    # Start bot
    async with bot:
        
        if BOT_TOKEN: await bot.start(BOT_TOKEN)

asyncio.run(main())
