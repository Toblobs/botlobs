# main.py // @toblobs // 21.03.26

from __init__ import *

import asyncio
import io
from discord.ext import tasks
from datetime import time
import re

from cogs.general_commands import send_about, send_introduction, send_bot_status
from cogs.xp_commands import send_leaderboard_graph, send_curve_graph
from cogs.fun_commands import send_qotd

from cogs.utils.embeds import basic_embed
from cogs.utils.emoji import get_emoji
from cogs.utils.permissions import *

import feedparser

class IntroView(discord.ui.View):
    
    def __init__(self, bot, wakeup):
        
        super().__init__(timeout = None)
        self.bot = bot
        self.wakeup = wakeup
        
    @discord.ui.button(label = "Open Introduction Form", style = discord.ButtonStyle.primary, custom_id = "intro_button")
    async def button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        
        await send_introduction(self.bot, self.wakeup, interaction)

class ReactionView(discord.ui.View):
    
    def __init__(self, bot, button_emojis):
        
        super().__init__(timeout = None)        
        self.bot = bot
        self.button_emojis = button_emojis
        
        for b in self.button_emojis: 
            self.add_item(discord.ui.Button(label = "", emoji = get_emoji(b), custom_id = b, style = discord.ButtonStyle.secondary))

class Automation(commands.Cog):
    
    def __init__(self, bot: commands.Bot, wakeup: asyncio.Event):
        
        self.bot = bot
        self.wakeup = wakeup
        
        self.midnight_tracker.start()
        self.youtube_checker.start()
        self.last_video_id = None
        
        self.responded_to_ids = []
        
    async def cog_unload(self):
        
        self.midnight_tracker.cancel()
        self.youtube_checker.cancel()

    @tasks.loop(minutes = 1)
    async def youtube_checker(self):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        channel_id = "UCPf8yBATA-GUaadwwZVDf-g"
        url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        
        feed = feedparser.parse(url)
        if not feed.entries: return
        
        latest_video = feed.entries[0]
        video_id = latest_video.yt_videoid
        video_url = latest_video.link
        
        if self.last_video_id is None:
            self.last_video_id = video_id
            return
        
        if video_id != self.last_video_id:
            
            self.last_video_id = video_id
            uploads_channel = guild.get_channel(1383390370251018240) # type: ignore
            supporter_role = guild.get_role(1140056781649887374) # type: ignore
            
            embed = basic_embed(title = "🎬 YouTube Upload",
                                description = f"Toblobs has posted a new YouTube video!\n> - **Video Link**: {video_url}\n> - **Posted On**: <t:{int(datetime.now().timestamp())}:D>",
                                bot = self.bot)
            
            embed.color = discord.Color.from_rgb(255, 0, 0)
            
            await uploads_channel.send(content = f"{supporter_role.mention} | {video_url}",  # type: ignore
                                       embed = embed)

    @tasks.loop(time = time(hour = 0, minute = 0)) 
    async def midnight_tracker(self):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        metrics_channel = self.bot.get_channel(1484642590115758210)
        
        # purge messages
        deleted = []

        async for msg in metrics_channel.history(limit = 1000): # type: ignore
            
            if msg.id <= 1484698421456797837: continue
            deleted.append(msg)
            
        for i in range(len(deleted)): await metrics_channel.delete_messages(deleted) # type: ignore
        
        # /about
        await metrics_channel.send(content = "", file = discord.File(BANNER_FOLDER + r"\about-banner-wide.png")) # type: ignore  
        await send_about(self.bot, guild, channel = metrics_channel)
        
        # /bot-status
        gen_cog = self.bot.get_cog("GeneralCommands")
        uptime = gen_cog.get_uptime() # type: ignore
        await metrics_channel.send(content = "", file = discord.File(BANNER_FOLDER + r"\statuses-banner-wide.png")) # type: ignore  
        await send_bot_status(self.bot, guild, channel = metrics_channel, uptime = uptime)
        
        # /status adder: needs activities plugin, later version
        
        # /leaderboard graphs
        await metrics_channel.send(content = "", file = discord.File(BANNER_FOLDER + r"\graphs-banner-wide.png")) # type: ignore  
        await send_leaderboard_graph(bot = self.bot, guild = guild, channel = metrics_channel)
        
        # /curve graph
        await send_curve_graph(bot = self.bot, guild = guild, channel = metrics_channel)
        
        # /quote
        await metrics_channel.send(content = "", file = discord.File(BANNER_FOLDER + r"\qotd-banner-wide.png")) # type: ignore  
        await send_qotd(bot = self.bot, guild = guild, channel = metrics_channel)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore

        here_we_go_channel = self.bot.get_channel(1138065390304514140)
        embed = basic_embed(title = "Member Join", description = f"{member.mention} joined **The Toblobs Lounge**!\n> - They are member: **#{sum(1 for m in guild.members if not m.bot)}**.\n> - They've **joined** on: <t:{int(datetime.now().timestamp())}:F>", bot = self.bot) # type: ignore
        embed.set_image(url = "attachments://welcome-image.png")
        
        await here_we_go_channel.send(content = f"{member.mention}", embed = embed, file = discord.File(BANNER_FOLDER + r"\welcome-banner-wide.png", filename = "welcome-image.png"), allowed_mentions = discord.AllowedMentions(roles = True, users = True)) # type: ignore
    
    @commands.Cog.listener()
    async def on_member_remove(self, member):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore

        here_we_go_channel = self.bot.get_channel(1138065390304514140)
        await here_we_go_channel.send(embed = basic_embed(title = "Member Leave", description = f"Member `{member.name}` has left **The Toblobs Lounge**.", bot = self.bot)) # type: ignore
        
        
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        metrics_channel = self.bot.get_channel(1484642590115758210)
        
        average_custom = guild.get_role(1462161257045168283) # type: ignore
        
        response_map = {"meow": "meow :3",
                        "good morning toblobsians": "🌞",
                        "egg": "<:eggblobs:1237872062211555378>",
                        "toblobs files": discord.Object(id = 1274379357045002243),
                        "phone is dying": "charge it with gasoline",
                        "regime": discord.Object(id = 1484723339305156649),
                        "lawyer": discord.Object(id = 1174286198563422208),
                        "so": "vie",
                        "nsfw": "Y’know, I’ve been wanting to say this for quite a while, however I didn’t have the guts. But oooooooh, you’ve really done it this time, man. Do you even know what you’ve done to this server? Nobody is having fun anymore, and ever since you all joined there’s no spirit left. This server wasn’t supposed to be your average camp. It’s supposed to be dirty, it’s supposed to have NSFW. And what the fuck is with the “illegal” shit? It’s not illegal, there’s a reason why sites like PornHub and Rule34 aren’t banned in most countries yet. And even if it is illegal, who’s gonna stop us? The government’s not gonna care if someone makes an art of two stickmen having sex, and if ya still couldn’t tell, no one in the roleplays are actually in a relationship together. Cayden and Edna are just friends. Me and Acid are just friends. We’re just screwing around, aka, having fun. But why, how is this fun, you may ask? Well, it’s simple. We’re teenagers and young adults. Teens and young adults do stupid stuff. All they want to do is be horny and shit. Who can blame us? Well, you apparently you. However, I realized that you guys are also probably teens and young adults, and look at you all shaming us. Well, the only thing I’m gonna to you guys is: Congrats. Congrats to not being like the rest of us. Congrats to not making inappropriate art and roleplays. Well time to finish this shit up. Fuck you for traumatizing my friends, really. You all are assholes who just won’t give a break. Look at what you all of you caused. Btw, this was the only server where I acted like this. And don’t even mention that thing I posted in Sebastianimania’s server. Oh, and good luck trying to get a reaction from me anymore. And if you’re confused, well, you’ll just find out. The only thing left I have to say is this: “Screw you guys, I’m going home!”",
                        "word limit": "> A gold plated sword to match the first,\n> A gold plated medal to win a curse.\n> Travel the broken path to hear the echo at the peak-\n> Word limits are for the weak.",
                        "zeta": "toblobs commits genocide with zeta",
                        "kevin": "kevin",
                        "theta": "nerf theta",
                        "president": "GET DOWN MR PRESIDENT",
                        "women": "nah i think im better than women",
                        "men": f'Auqog, Blitz, Ryan: "where"',
                        "fog": "`t h e f o g i s c o m i n g`",
                        "sub": "*less",
                        "9/11": "but the mods hit the plane",
                        "antagonist": discord.Object(id = 1259556878157873392),
                        "how tired": f"{average_custom.mention if average_custom else "too tired to sleep"}",
                        "ship": "xen did not die for ts",
                        "race": "n tier",
                        "gentlemen": "its a mystery",
                        "gng": "good night girl",
        }
        
        def contains_phrase(text, phrase):
            pattern = r"\b" + re.escape(phrase) + r"\b"
            return re.search(pattern, text, re.IGNORECASE) is not None

        if message.author.bot: return
        if message.channel.id == SHADY_LOUNGE_ID:
            
            for key, resp in response_map.items():
                
                if contains_phrase(message.content.lower(), key) and message.id not in self.responded_to_ids:
                    
                    if isinstance(resp, str): await message.reply(resp)
                    elif isinstance(resp, discord.Object): await message.reply(content = "", stickers = [resp]) # type: ignore
                    
                    self.responded_to_ids.append(message.id)
                    
    
    @commands.Cog.listener()
    async def on_message_delete(self, interaction):
        
        if interaction.author.bot: return
        
        user = interaction.author
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        logs_channel = guild.get_channel(1140063993034199091) # type: ignore
        
        embed = basic_embed(title = "Message Deleted", description = "", bot = self.bot)
        embed.color = discord.Color.red()
        
        embed.add_field(name = "Author", value = f"{user} (`{user.id}`)", inline = False) # type: ignore
        embed.add_field(name = "Channel", value = interaction.channel.mention if interaction.channel else "`N/A`", inline = False) # type: ignore
        
        content = interaction.content if interaction.content else "[Content unknown/uncached]" # type: ignore
        embed.add_field(name = "Content", value = content, inline = False)

        file_attach = []
        
        if interaction.attachments: 
            
            embed.add_field(name = "Attachments", value = f"{len(interaction.attachments)} file(s)")
            
            for attachment in interaction.attachments:
                
                file_bytes = await attachment.read()
                file_attach.append(discord.File(io.BytesIO(file_bytes), filename = attachment.filename))
                    
        await logs_channel.send(embed = embed, files = file_attach) # type: ignore
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        
        if before.author.bot: return
        if before.content == after.content: return

        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        logs_channel = guild.get_channel(1140063993034199091) # type: ignore
        
        embed = basic_embed(title = "Message Edited", description = "", bot = self.bot)
        embed.color = discord.Color.orange()
        
        embed.set_author(name = f"{before.author}", icon_url = before.author.display_avatar.url)
        
        embed.add_field(name = "Before", value = before.content or "[Unknown]", inline = False)
        embed.add_field(name = "After", value = after.content or "[Unknown]", inline = False)
        embed.add_field(name = "Link to Message", value = f"{after.jump_url}")
        
        embed.set_footer(text = f"User ID: {before.author.id}")

        await logs_channel.send(embed = embed) # type: ignore
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        
        if interaction.type == discord.InteractionType.application_command:
            
            guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
            logs_channel = guild.get_channel(1140063993034199091) # type: ignore
            
            command_name = interaction.data.get('name') # type: ignore
            options = interaction.data.get('options', []) # type: ignore
            
            user = interaction.user
            
            if interaction.channel_id == 1140063993034199091: return
            
            embed = basic_embed(title = "Command Usage", 
                        description = f"**Command:** **`{command_name}`**",
                        bot = self.bot)

            embed.add_field(name = "User", value = f"{user} (`{user.id}`)", inline = False) # type: ignore
            embed.add_field(name = "Channel", value = interaction.channel.mention if interaction.channel else "`N/A`", inline = False) # type: ignore
            
            for opt in options:
                embed.add_field(name = f"`{opt.get("name")}:`", value = f"`{opt.get("value")}`", inline = True)
                
            await logs_channel.send(embed = embed) # type: ignore
            
        elif interaction.data:
            
            guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
            metrics_channel = self.bot.get_channel(1484642590115758210)
                
            if interaction.data.get("custom_id"):
                
                emoji_loookup = {"miscannouncements": 1154296386469232693,
                                "eventannouncements": 1154296321897926676,
                                
                                "videogames": 1203257064646901790,
                                "algodoo": 1203257137547972619,
                                "artandcreatives": 1203257239859765268,
                                "music": 1203257388409557022,
                                "writingandbooks": 1203257426141519882,
                                "sports": 1203257470873509889,
                                "pollnotifs": 1303784133578719366,
                                
                                "redtie": 1140058151127887893,
                                "tangerina": 1140058044215066734,
                                "scottishxanadu": 1140057941010022451,
                                
                                "saffronshades": 1237465948055933059,
                                "tealoblobs": 1237465819450179674,
                                "carminecuffs": 1237465605230035056,
                                
                                "tobluebs": 1237473082923286528,
                                "blossomblitz": 1237474170624016527,
                                "celadoncultist": 1237474304229113908}
                
                found_role = False
                
                if interaction.data["custom_id"] in ["miscannouncements", "eventannouncements", "videoganmes", "algodoo", "artandcreatives", "music", "writingandbooks", "sports", "pollnotifs"]: # type: ignore
                    
                    role = guild.get_role(emoji_loookup[interaction.data["custom_id"]]) # type: ignore
                    if role not in interaction.user.roles: # type: ignore
                        
                        await interaction.user.add_roles(role) # type: ignore
                        found_role = True
                    
                    else:
                        
                        if not interaction.response.is_done(): await interaction.response.send_message(embed = basic_embed(title = "Role Selector", description = "You already have this role!", bot = self.bot), ephemeral = True)
                
                elif interaction.data["custom_id"] in ["redtie", "tangerina", "scottishxanadu", "saffronshades", "tealoblobs", "carminecuffs", "tobluebs", "blossomblitz", "celadoncultist"]: # type: ignore 
                    
                    for (rank, shades_role_list) in [(is_at_least_level(interaction.user, SHADES_ROLE), ["redtie", "tangerina", "scottishxanadu"]), # type: ignore
                                                    (is_at_least_level(interaction.user, SHADES_PLUS_ROLE), ["saffronshades", "tealoblobs", "carminecuffs"]), # type: ignore
                                                    (is_at_least_level(interaction.user, SHADES_PLUS_PLUS_ROLE), ["tobluebs", "blossomblitz", "celadoncultist"])]: # type: ignore

                        role = guild.get_role(emoji_loookup[interaction.data["custom_id"]]) # type: ignore
                        if rank and interaction.data["custom_id"] in shades_role_list and role not in interaction.user.roles: #type: ignore
                            
                            roles = [guild.get_role(emoji_loookup[e]) for e in shades_role_list] # type: ignore
                            await interaction.user.remove_roles(*roles) # type: ignore
                            await interaction.user.add_roles(role) # type: ignore
                            found_role = True
                        
                        elif role in interaction.user.roles: # type: ignore
                            
                            if not interaction.response.is_done(): await interaction.response.send_message(embed = basic_embed(title = "Role Selector", description = "You already have this role!", bot = self.bot), ephemeral = True)

                        elif interaction.data["custom_id"] in shades_role_list and not rank: # type: ignore
                            
                            if not interaction.response.is_done(): await interaction.response.send_message(embed = basic_embed(title = "Role Selector", description = "You're not ranked high enough for this role yet.", bot = self.bot), ephemeral = True)

                if found_role and not interaction.response.is_done(): await interaction.response.send_message(embed = basic_embed(title = "Role Selector", description = "Role added successfully!", bot = self.bot), ephemeral = True)
                