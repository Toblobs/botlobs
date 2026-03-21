# cogs > general.py // @toblobs // 21.03.26

from datetime import timedelta
from dateutil import relativedelta

from .__init__ import *

import re
import io
import time
import asyncio
import psutil
import uuid

from typing import List, Tuple
from copy import copy

from discord import TextChannel, app_commands
from discord.ext import commands

import numpy as np
from PIL import Image
import emoji

import matplotlib.pyplot as plt 
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator, StrMethodFormatter
from matplotlib.lines import Line2D

from cogs.utils.embeds import basic_embed
from cogs.utils.permissions import *
from cogs.utils.emoji import *
from cogs.utils.convert import *

from database import xp, reminders, users

async def send_about(bot, guild, channel = None, interaction = None):
    
    INVITE_CODE = "X53PzUqAvK"
    guild = bot.get_guild(int(GUILD_ID)) # type: ignore
    banner = guild.banner # type: ignore

    information = {f"{get_emoji("botlobs")} **Server ID**": f"`{GUILD_ID}`", f"{get_emoji("lapislapels")} **Owner**": f"{bot.get_user(762238670656634921).mention}", f"{get_emoji("blob")} **Members**": f"`{sum(1 for m in guild.members if not m.bot)}`", # type: ignore
                    f"{get_emoji("artandcreatives")} **Created At**": f"<t:{int(guild.created_at.timestamp())}:D>", f"{get_emoji("admin")} **Opened At**": f"<t:1695164400:D>", f"{get_emoji("serverbooster")} **Boost Level**": f"Level `{guild.premium_tier}` (`{guild.premium_subscription_count}` Boosts)", # type: ignore
                    f"{get_emoji("blacktie")} **Roles**": f"`{len(guild.roles)}`", f"{get_emoji("writingandbooks")} **Categories**": f"`{len([c for c in guild.channels if isinstance(c, discord.CategoryChannel)])}`", f"{get_emoji("irlfriends")} **Default Role**": f"{guild.get_role(1139122746199134249).mention}", # type: ignore
                    f"{get_emoji("suit")} **Text Channels**": f"`{len([c for c in guild.channels if isinstance(c, discord.TextChannel)])}`", f"{get_emoji("music")} **Voice Channels**": f"`{len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])}`", f"{get_emoji("cluefinder")} **This Channel**": f"{interaction.channel.mention if interaction else channel.mention}", # type: ignore
                    f"{get_emoji("scarfman")} **Emojis**": f"`{len(guild.emojis)}`", f"{get_emoji("bots")} **Bots**": f"`{sum(1 for m in guild.members if m.bot)}`", f"{get_emoji("eventannouncements")} Invite Code:": f"https://discord.com/invite/{INVITE_CODE}", # type: ignore
    }

    e = discord.Embed(title = "The Toblobs Lounge: About Page", color = DEFAULT_COLOR, timestamp = datetime.now())
    e.set_author(name = f"BotLobs", icon_url = bot.user.display_avatar.url) # type: ignore

    for name, data in information.items(): e.add_field(name = name, value = data, inline = True)

    if banner:
        e.add_field(name = "**Server Banner**:", value = "\u200b")
        e.set_image(url = banner.url)

    e.set_thumbnail(url = bot.user.display_avatar.url) # type: ignore
    
    if interaction: await interaction.response.send_message(embed = e)
    elif channel: await channel.send(embed = e)

async def send_introduction(bot, wakeup, interaction = None):
    
    guild =  bot.get_guild(int(GUILD_ID)) # type: ignore
    member = interaction.user # type: ignore
        
    class IntroductionModal(discord.ui.Modal):
        
        def __init__(self, bot, wakeup: asyncio.Event):
            
            super().__init__(title = "Introduction Form")
            
            self.add_item(discord.ui.TextInput(label = "About Me", placeholder = "Enter your introdution text here...", style = discord.TextStyle.paragraph))
            self.add_item(discord.ui.TextInput(label = "Birthday", placeholder = "Your birthday in format (DD-MM), eg. 24-07 (optional)", required = False))
            self.add_item(discord.ui.TextInput(label = "Country", placeholder = "Copypaste a Unicode country emoji into here... (optional)", required = False))

            self.bot = bot
            self.wakeup = wakeup
        
        def next_date(self, dt):
            
            try:
                
                today = datetime.today()
                target = datetime(year = today.year, month = dt.month, day = dt.day) # type: ignore
            
            except:
                
                raise ValueError("Invalid day/month combination.")
            
            if target <= today:
                target = datetime(year = today.year + 1, month = dt.month, day = dt.day) # type: ignore
            
            return target
            
        async def on_submit(self, interaction: discord.Interaction):
            
            about_me = self.children[0].value # type: ignore
            birthday = self.children[1].value # type: ignore
            country = self.children[2].value # type: ignore
            
            try:
                
                if birthday: 
                    try: _date = datetime.strptime(birthday, "%d-%m") 
                    except ValueError: raise AssertionError(f"`date` is not a valid date")
                
                else: _date = 0
                
                if country: assert emoji.is_emoji(country), f"`country` is not is not an emoji"
            
            except AssertionError as e:
                
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
                return

            if _date: target_date = int(self.next_date(_date).timestamp())
            else: target_date = None

            await users.set_user_intro(member.id, about_me, target_date, country)
            await interaction.response.send_message(embed = basic_embed(title = "Introduction Form", description = f"Introduction set.", bot = self.bot), ephemeral = True)
                
    if interaction: await interaction.response.send_modal(IntroductionModal(bot = bot, wakeup = wakeup))

async def send_bot_status(bot, guild, channel, uptime):

    process = psutil.Process(os.getpid())

    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    
    # Generate embed
    e = discord.Embed(title = "Bot Status", color = DEFAULT_COLOR, timestamp = datetime.now())
    e.set_author(name = f"BotLobs", icon_url = bot.user.display_avatar.url) # type: ignore
    
    e.description = f"""An open source Discord bot, written to power The Toblobs Lounge.\n## __Bot Information__
    > - **Current Version**: `v{VERSION}` (last updated <t:1774051200:R>)
    > - **Codebase**: {GITHUB_LINK}
    > - **Documentation & Help**: *Coming soon...*
    ## __Program Information__
    > - **Uptime**: `{uptime}`    
    """
    
    await channel.send(embed = e)

class GeneralCommands(commands.Cog):

    def __init__(self, bot: commands.Bot, wakeup: asyncio.Event):

        self.bot = bot
        self.wakeup = wakeup

        self.start_time = time.time()
        self.process = None
        
    ### generally used submodules

    def hex_to_rgb(self, hex: str) -> tuple:

        if hex[0] == '#': 
            stripped = hex.lstrip('#')
            
        else: 
            stripped = hex

        return tuple(int(stripped[i: i + 2], 16) for i in (0, 2, 4))

    def parse_colors(self, text: str, max_colors: int = 8) -> List[str]:
        

        HEX_PATTERN = re.compile(r"^#?([0-9A-Fa-f]{6})$")
        
        text = text.strip()

        if HEX_PATTERN.match(text):
            
            return [HEX_PATTERN.match(text).group(1).upper()] # type: ignore

        if text.startswith('[') and text.endswith(']'):

            inner = text[1:-1]

            parts = [p.strip() for p in inner.split(",")]

            if len(parts) == 0:
                raise ValueError("Empty color sequence.")
            
            if len(parts) > max_colors:
                raise ValueError(f"`{len(parts)}` colors provided, the maximum is `{max_colors}` colors.")
            
            colors = []

            for p in parts:
                
                m = HEX_PATTERN.match(p)

                if not m:
                    raise ValueError(f"Invalid hex color: `{p}`.")
                
                colors.append(m.group(1).upper())
            
            return colors

        raise ValueError("Invalid format: use either `RRGGBB` or `[RRGGBB, RRGGBB, ...]`.")

    def generate_color_image(self, size: Tuple[int, int], hexes_list: List[str]) -> io.BytesIO:

        img = Image.new("RGB", size)
        pixels = img.load()

        colors = [self.hex_to_rgb(h) for h in hexes_list]
        segments = len(colors) - 1

        for x in range(size[0]):
            
            if x > 0:
                
                pos = x / (size[0] - 1)
                segment = min(int(pos * segments), segments - 1)

                local_pos = (pos* segments) - segment

                c1 = colors[segment]
                c2 = colors[segment + 1]

                r = int(c1[0] + (c2[0] - c1[0]) * local_pos)
                g = int(c1[1] + (c2[1] - c1[1]) * local_pos)
                b = int(c1[2] + (c2[2] - c1[2]) * local_pos)

                for y in range(size[1]):
                    pixels[x, y] = (r, g, b) # type: ignore

        buffer = io.BytesIO()
        img.save(buffer, "PNG")
        buffer.seek(0)
        
        return buffer
    
    def get_uptime(self):
            
            seconds = int(time.time() - self.start_time)
            return f"{seconds // 3600}h {(seconds % 3600) // 60}m {seconds % 60}s"
        
    ### commands
    
    # /help
    @app_commands.command(name = "help", description = "Shows a list of all commands.")
    @app_commands.describe(page = "The page to jump to, optional", command = "The command to jump to, optional")
    async def help(self, interaction: discord.Interaction, page: int = 1, command: str | None = None):
        
        async def build_help_embed(page):
            
            e = discord.Embed(title = "Help Pages", color = DEFAULT_COLOR, timestamp = datetime.now())
            e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

            file = discord.File(HELP_PAGES_FOLDER + rf"\page-{page:02}.png", filename = "helppage.png")
            e.set_image(url = "attachment://helppage.png")
            
            e.description = "Browse the help pages."
            
            e.set_footer(text = f"Page {page}")
            return (e, file)
        
        class PageSelect(discord.ui.Select):
            
            def __init__(self, parent_view: discord.ui.View):
                
                self.parent_view = parent_view
                total_pages = 24
                
                options = []
                
                for page in range(1, total_pages + 1):

                    options.append(discord.SelectOption(label = f"Page {page}", value = str(page)))
                    super().__init__(placeholder = "Jump to page...", min_values = 1, max_values = 1, options = options)
            
            async def callback(self, interaction: discord.Interaction):

                page = int(self.values[0])
                self.parent_view.page = page # type: ignore

                e, file = await self.parent_view.load_page() # type: ignore

                await interaction.response.edit_message(embed = e, view = self.parent_view, attachments = [file])

            async def interaction_check(self, interaction) -> bool:
                return interaction.user.id == self.parent_view.user_id # type: ignore
        
        class HelpView(discord.ui.View):
            
            def __init__(self, interaction, page = 1):

                super().__init__(timeout = 300)

                self.user_id = interaction.user.id
                self.page = page
                self.add_item(PageSelect(self))

            async def load_page(self): return await build_help_embed(self.page)

            @discord.ui.button(label = "◀ Previous")
            async def previous(self, interaction, button):

                if self.page > 1:
                    self.page -= 1
                
                embed, file = await self.load_page()
                await interaction.response.edit_message(embed = embed, view = self, attachments = [file])

            @discord.ui.button(label = "Next ▶")
            async def next(self, interaction, button):

                self.page += 1
                
                embed, file = await self.load_page()
                await interaction.response.edit_message(embed = embed, view = self, attachments = [file])
        
        commands_to_page = {
                            # General Commands
                            "help": 6, "about": 6, "info": 6, "birthdays": 7, "role": 7, "channel": 7, "ping": 7,
                            "avatar": 7, "banner": 8, "suggest": 8, "remind": 8, "embed": 8, "convert": 8, "edit-image": 9,
                            "color": 9, "roll": 9, "introduce": 10, "bot-status": 10,
                            
                            # XP Commands
                            "leaderboard": 11, "curve": 11, "multipliers": 11, "sync": 12, "rank": 12, "calculate": 12,
                            "prestige-shop": 12, "black-tie": 12, "custom": 12,
                            
                            # Fun Commands
                            "topic": 14, "two-o-four-eight": 14, "quote": 14, "tierlist": 14, "event": 15, "play": 15,
                            "controller": 15, "remove": 16,
                            
                            # Staff Commands
                            "xp-set": 17, "multipliers-set": 17, "nick-set": 18, "mute": 18, "unmute": 18, "kick": 18,
                            "ban": 19, "giveaway": 19, "purge": 20, "lock": 20, "quote-bank": 20, "custom-set": 21, "remove-reminder": 21,
                            
                            # Tobs Commands & Passive
                            "status": 22, "restart": 22, "passive": 23
                            }
        
        if page is None: page = 1
        
        if not (1 <= page <= 24):
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"`page` must be between `1` and `24.", bot = self.bot), ephemeral = True)
            return
        
        if command is not None:
            
            if command.lower() not in commands_to_page.keys():
                
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not find this `command`.", bot = self.bot), ephemeral = True)
                return

            page = commands_to_page[command.lower()]
        
        view = HelpView(interaction, page = page)

        e, file = await view.load_page()
        await interaction.response.send_message(embed = e, view = view, file = file)

    # /about
    @app_commands.command(name = "about", description = "Shows the info page for the server.")
    async def about(self, interaction: discord.Interaction):
        
        await send_about(self.bot, self.bot.get_guild(int(GUILD_ID)), interaction = interaction) # type: ignore

    # /info
    @app_commands.command(name = "info", description = "Shows the info page for a server member.")
    async def info(self, interaction: discord.Interaction, member: discord.Member | None = None):

        member = member or interaction.user # type: ignore

        if not member: 

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not fetch info about this member.", bot = self.bot), ephemeral = True)
            return
        
        try:
            current_xp, level, prestige, intro_text, birthday, country = await users.get_user(member.id) # type: ignore
        
        except:
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not fetch info about this member.", bot = self.bot), ephemeral = True)
            return
        
        information = {"mention": f"{member.mention}", "name": f"`{member.name}`", "id": f"`{member.id}`",
                       "joined": f"<t:{int(member.joined_at.timestamp())}:D> (<t:{int(member.joined_at.timestamp())}:R>)", "registered": f"<t:{int(member.created_at.timestamp())}:D> (<t:{int(member.created_at.timestamp())}:R>)", # type: ignore
                       "roles": member.roles, "permissions": [], "acknowledgments": [], "intro_text": intro_text, "birthday": birthday, "country": country, "thumbnail": ""} 

        # Get permissions
        for perm_name, value in member.guild_permissions:

                if value and perm_name in ["administrator", "manage_channels", "ban_members", "kick_members", "manage_messages",
                                           "manage_roles", "manage_nicknames", "manage_webhooks", "manage_server", "manage_emojis_and_stickers",
                                           "mention_everyone", "timeout_members"]:

                    information["permissions"].append(perm_name.replace("_", " ").title())

        # Get Acknowledgments
        if TOBLOBS_ROLE in member.roles: information["acknowledgments"].append("Server Owner")
        elif member.guild_permissions.administrator: information["acknowledgments"].append("Server Administrator")
        elif is_moderator(member): information["acknowledgments"].append("Server Moderator")
        elif is_staff(member): information["acknowledgments"].append("Server Junior Moderator")

        if member.premium_since: information["acknowledgments"].append("Server Booster")
        elif ELITIST_ROLE in member.roles: information["acknowledgments"].append("Elitist")

        # Get avatar
        fmt = "gif" if member.display_avatar.is_animated() else "png" # type: ignore
        information["thumbnail"] = member.display_avatar.with_format(fmt).with_size(256).url # type: ignore
        
        # Get color
        top_colored_role = get_top_colored_role(member)
        
        # Generate embed
        e = discord.Embed(title = "Member Information", color = top_colored_role.color if top_colored_role else DEFAULT_COLOR, timestamp = datetime.now(), description = information["mention"])
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

        e.add_field(name = "Name", value = information["name"], inline = True)
        e.add_field(name = "ID", value = information["id"], inline = True)
        e.add_field(name = "\u200b", value = "\u200b", inline = True)

        e.add_field(name = "Joined at:", value = information["joined"], inline = True)
        e.add_field(name = "Registered at:", value = information["registered"], inline = True)
        e.add_field(name = "\u200b", value = "\u200b", inline = True)

        if information["roles"]:

            end = 30 if len(member.roles) > 30 else len(member.roles)
            roles_str = ""

            reverse = list(information["roles"])[::-1]
            for r in reverse[0:(end - 1)]:
                roles_str += f"{r.mention} " # type: ignore

            if len(member.roles) > 30:
                roles_str += f"...(showing first **30** roles)" # type: ignore

            e.add_field(name = "Roles", value = roles_str, inline = False) # type: ignore

        if information["permissions"]:
            e.add_field(name = "Key Permissions", value = ", ".join(information["permissions"]), inline = False)

        if information["acknowledgments"]:
            e.add_field(name = "Acknowledgments", value = ", ".join(information["acknowledgments"]), inline = False)

        if information["intro_text"]:
            e.add_field(name = "Introduction", value = information["intro_text"], inline = False)
            
        if information["birthday"]:
            e.add_field(name = "Next Birthday", value = f"<t:{information["birthday"]}:D> (<t:{information["birthday"]}:R>)", inline = True)
        
        if information["country"]:
            e.add_field(name = "Country", value = information["country"], inline = True)
            
        e.set_thumbnail(url = information["thumbnail"])
        await interaction.response.send_message(embed = e)

    # /birthdays
    @app_commands.command(name = "birthdays", description = "Shows birthdays in the server.")
    @app_commands.describe(month = "Month to look for birthdays for, optional", timezone = "Timezone to offset by, e.g. -5 for GMT-5, optional")
    async def birthdays(self, interaction: discord.Interaction, month: str | None = None, timezone: int | None = 0):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        if not timezone: timezone = 0
        
        if not -12 <= timezone <= 12:
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Invalid `timezone` given - must be between `-12` and `12`, e.g. `-5` for the GMT-5 timezone.", bot = self.bot), ephemeral = True) # type: ignore
            return
        
        months = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
        month_int = 0
        
        if not month: month_int = datetime.now().month - 1
        
        elif month.lower().strip() not in months:
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Invalid `month` given - must be one of {", ".join([m.title() for m in months])}.", bot = self.bot), ephemeral = True) # type: ignore
            return

        else: month_int = months.index(month.lower().strip())
        
        birthdays = []
        all_users = await users.get_all_users()
        
        for (user_id, _xp, level, prestige, intro_text, birthday, country) in all_users:
            
            if birthday:
                
                birthday_month = datetime.fromtimestamp(int(birthday)).month
                if birthday_month == month_int + 1: birthdays.append((user_id, int(birthday) + (-1 * timezone * 3600)))
        
        birthdays = sorted(birthdays, key = lambda x: x[1])
        
        members_text = ""
        
        for b in birthdays:
            
            user_id, timestamp = b
            
            member = guild.get_member(user_id) # type: ignore

            members_text += f"\n{member.mention if member else "???"} | <t:{timestamp}:D>"
        
        if len(birthdays) > 30: members_text += " ... (showing first **30** members)"
        
        await interaction.response.send_message(embed = basic_embed(title = f"Member Birthdays in {months[month_int].title()}", description = members_text, bot = self.bot))
            
    # /role
    @app_commands.command(name = "role", description = "Show the info page for a server role.")
    @app_commands.describe(role = "Role to get info about.", members = "Fetch up to 30 members who have this role, server moderators only.")
    async def role(self, interaction: discord.Interaction, role: discord.Role, members: bool = False):
        
        if members and not is_moderator(interaction.user): # type: ignore

            guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Using `member` is a permission for {guild.get_role(MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return

        else:
            
            guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore

            information = {"id": f"`{role.id}`", "name": f"{role.name}", "hexes": "", "mention": f"{role.mention}", "hoisted": f"`{role.hoist}`", 
                           "position": f"`{role.position}` (`{len(guild.roles) - role.position}` from top)", "mentionable": f"`{role.mentionable}`", f"managed": f"`{role.managed}`", "permissions": [], "created at": f"<t:{int(role.created_at.timestamp())}:F>", # type: ignore
                           "thumbnail": "", "members": [], }

            # Get hexes and thumbnail

            file = None

            information["hexes"] = [f"{role.color.value:06X}"] # default if no gradient

            if role.secondary_color: # type: ignore
                information["hexes"].append(f"#{role.secondary_color.value:06X}") # type: ignore

            if role.tertiary_color: # type: ignore
                information["hexes"].append(f"#{role.tertiary_color.value:06X}") # type: ignore

            if role.icon:
                information["thumbnail"] = role.icon.with_size(256).url

            else:

                buffer = self.generate_color_image((1024, 256), information["hexes"]) # type: ignore

                file = discord.File(buffer, filename = "role_thumbnail.png")
                information["thumbnail"] = "attachment://role_thumbnail.png"

            # Get permissions

            for perm_name, value in role.permissions:

                if value and perm_name in ["administrator", "manage_channels", "ban_members", "kick_members", "manage_messages",
                                           "manage_roles", "manage_nicknames", "manage_webhooks", "manage_server", "manage_emojis_and_stickers",
                                           "mention_everyone", "timeout_members"]:

                    information["permissions"].append(perm_name.replace("_", " ").title())
    
            # Get members   
            if members:
                information["members"] = [m.name for m in role.members[:30]]
            
            # Generate embed
            e = discord.Embed(title = "Role Information", color = role.color, timestamp = datetime.now())
            e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

            for field in ["id", "name", "mention", "hoisted", "position", "mentionable", "managed", "created at"]:
                e.add_field(name = field.title(), value = information[field], inline = True)

            if information["hexes"]:

                hex_text = ""

                for hex in information["hexes"]:
                    
                    if information["hexes"].index(hex) != len(information["hexes"]) - 1:
                        hex_text += f"`#{hex}`, "

                    else:
                        hex_text += f"`#{hex}`"

                e.add_field(name = "Hexes", value = hex_text)

            if information["permissions"]:
                e.add_field(name = "Key Permissions", value = ", ".join(information["permissions"]), inline = False)

            if information["members"]:

                members_text =  ""

                for i in information["members"]:

                    members_text += f"`{i}`\n"

                if len(role.members) > 30:

                    members_text += " ... (showing first **30** members)"

                e.add_field(name = "Members", value = members_text, inline = False)

            if file: e.set_thumbnail(url = await upload_asset(self.bot, file))
            else: e.set_thumbnail(url = information["thumbnail"])
            await interaction.response.send_message(embed = e)
    
    # /channel
    @app_commands.command(name = "channel", description = "Shows the info page for a channel.")
    @app_commands.describe(channel = "Channel to get info about, defaults to this channel.")
    async def channel(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None):
    
        if not isinstance(interaction.channel, TextChannel) and not isinstance(channel, TextChannel):
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"This command must be used from a text channel if `channel` is not provided.", bot = self.bot), ephemeral = True)
            return
        
        channel = channel or interaction.channel # type: ignore

        information = {"id": f"`{channel.id}`", "name": f"{channel.name}", "category": f"{channel.category.name if channel.category else "N/A"}", "mention": f"{channel.mention}", # type: ignore
                       "position": f"`{channel.position}`", "topic": f"{channel.topic}", f"nsfw": f"`{channel.is_nsfw()}`", "created at": f"<t:{int(channel.created_at.timestamp())}:F>", # type: ignore
                       "recent messages (cooldown)": 0}

        message_count = await xp.count_messages(channel.id, int(time.time()) - 86400) # type: ignore
        information["recent messages (cooldown)"] = f"**`{message_count:,}`**"

        # Generate thumbnail
        def starts_with_emoji(name: str) -> str | None:
            first_char = name[0] if name else ""
            return first_char if emoji.is_emoji(first_char) else None 

        emoji_char = starts_with_emoji(channel.name) # type: ignore
        if not emoji_char: emoji_char = "#️⃣"

        codepoint = f"{ord(emoji_char):x}"
        link = f"https://twemoji.maxcdn.com/v/latest/72x72/{codepoint}.png"

        # Generate embed
        e = discord.Embed(title = "Channel Information", color = DEFAULT_COLOR, timestamp = datetime.now())
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

        e.set_thumbnail(url = link)

        for field in ["id", "name", "category", "mention", "position", "topic", "nsfw", "created at", "recent messages (cooldown)"]:
            e.add_field(name = field.title(), value = information[field], inline = True)
        
        await interaction.response.send_message(embed = e)

    # /ping
    @app_commands.command(name = "ping", description = "Tests the bot's latency.")
    async def ping(self, interaction: discord.Interaction):
        
        time_taken = (interaction.created_at - datetime.now(timezone.utc)).microseconds / 1000
        await interaction.response.send_message(embed = basic_embed(title = "Pong!", description = f"Responded in `{time_taken}` ms.", bot = self.bot))

    # /avatar
    @app_commands.command(name = 'avatar', description = "Shows a member's avatar.")
    @app_commands.describe(member = "Member to get avatar from, defaults to user", resolution = "Square power-of-two resolution to obtain avatar in.", local = "Whether to fetch their server or default avatar.")
    async def avatar(self, interaction: discord.Interaction, member: discord.Member | None = None, resolution: int = 2048, local: bool = True):

        RESOLUTIONS_ALLOWED = [16, 32, 64, 128, 256, 512, 1024, 2048]

        if resolution not in RESOLUTIONS_ALLOWED:
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Resolution `{resolution}` is not in `{RESOLUTIONS_ALLOWED}` valid resolutions.", bot = self.bot), ephemeral = True)
            return

        member = member or interaction.user # type: ignore

        if not member: 

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not fetch this member's avatar.", bot = self.bot), ephemeral = True)
            return
            
        if (member.display_avatar and local) or (member.avatar and not local): # type: ignore
            
            if local: 
                fmt = "gif" if member.display_avatar.is_animated() else "png" # type: ignore
                link = member.display_avatar.with_format(fmt).with_size(resolution).url # type: ignore
                title = f"Server Avatar"

            else:
                fmt = "gif" if member.avatar.is_animated() else "png" # type: ignore
                link = member.avatar.with_format(fmt).with_size(resolution).url # type: ignore
                title = f"Default Avatar"

            e = discord.Embed(title = title, description = member.mention + " **" + title + "**", color = DEFAULT_COLOR, timestamp = datetime.now()) # type: ignore
            e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

            e.set_image(url = link)

            await interaction.response.send_message(embed = e, allowed_mentions = discord.AllowedMentions(users = True))

        else:

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not fetch this member's avatar.", bot = self.bot), ephemeral = True)
            return

    # /banner
    @app_commands.command(name = 'banner', description = "Shows a member's global banner.")
    @app_commands.describe(member = "Member to get avatar from, defaults to user")
    async def banner(self, interaction: discord.Interaction, member: discord.Member | None = None):
    
        member = member or interaction.user # type: ignore
        member_user = await self.bot.fetch_user(member.id) # type: ignore

        if not member_user.banner: 

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not fetch this member's banner.", bot = self.bot), ephemeral = True)
            return
        
        else:

            fmt = "gif" if member_user.banner.is_animated() else "png" # type: ignore
            link = member_user.banner.with_format(fmt).with_size(2048).url
            
            e = discord.Embed(title = "Default Banner", description = member.mention + " **Default Banner**", color = DEFAULT_COLOR, timestamp = datetime.now()) # type: ignore
            e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

            e.set_image(url = link)

            await interaction.response.send_message(embed = e, allowed_mentions = discord.AllowedMentions(users = True))

    # /suggest
    @app_commands.command(name = 'suggest', description = "A temporary command allowing one to suggest an idea to the staff.")
    async def suggest(self, interaction: discord.Interaction):
    
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        suggest_channel = guild.get_channel(1153718764026736671) # type: ignore
        staff_role = guild.get_role(1140049417626464316) # type: ignore
        
        member = interaction.user # type: ignore
        
        class SuggestionModal(discord.ui.Modal):
            
            def __init__(self, bot):
                
                super().__init__(title = "Introduction Form")
                
                self.add_item(discord.ui.TextInput(label = "Suggestion", placeholder = "Add your suggestion here...", style = discord.TextStyle.paragraph))

                self.bot = bot
                
            async def on_submit(self, interaction: discord.Interaction):
                
                suggestion = self.children[0].value # type: ignore
                
                await suggest_channel.send(content = f"{staff_role.mention}", embed = basic_embed(title = "Suggestion", description = suggestion + f"\n## Sent by {member.mention}", bot = self.bot)) # type: ignore
                
                await interaction.response.send_message(embed = basic_embed(title = "Suggestion Form", description = f"Suggestion sent.", bot = self.bot), ephemeral = True)
            
        await interaction.response.send_modal(SuggestionModal(bot = self.bot))
            
    # /remind
    @app_commands.command(name = "remind", description = "Sets a reminder that can be reoccuring.")
    @app_commands.describe(time = "How long until the reminder triggers", message = "Message to send along with reminder, optional", repeat = "How long until the reminder repeats, optional", channel = "Channel to send the reminder to, optional")
    async def remind(self, interaction: discord.Interaction, time: str, message: str | None = None, repeat: str | None = None, channel: discord.TextChannel | None = None):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        bot_channel = guild.get_channel(1138183014178902097) # type: ignore
        
        def get_user_role_limits(member: discord.Member):

            ROLE_LIMITS = [(1140049990677450802, {"non_repeat": 50, "repeat": 5}),
                           (1140049956829405184, {"non_repeat": 30, "repeat": 3}),
                           (1140049921500795141, {"non_repeat": 30, "repeat": 3}),
                           (1140049851850162226, {"non_repeat": 20, "repeat": 0}),
                           (1140049746908684399, {"non_repeat": 20, "repeat": 0}),
                           (1140049685885767692, {"non_repeat": 20, "repeat": 0}),
                           (1140049620857266257, {"non_repeat": 10, "repeat": 0}),
                           (1139122746199134249, {"non_repeat": 10, "repeat": 0})]

        
            for (role_id, limits) in ROLE_LIMITS:
                
                role = guild.get_role(role_id) # type: ignore
                if role in member.roles: return limits
                
            return {"non_repeat": 10, "repeat": 0}
        
        MAX_YEARS = 10
        now = datetime.now()
        
        try:
            
            future = now + parse_time_string(time) # type: ignore
        
        except ValueError as e:

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{str(e).title()}.", bot = self.bot), ephemeral = True)
            return
        
        MAX_YEARS = 10
         
        max_future = now + relativedelta(years = MAX_YEARS)  # type: ignore
        
        if future > max_future:
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Time cannot be more than `10` years into the future.", bot = self.bot), ephemeral = True)
            return
        
        future_timestamp = int(future.timestamp())
        
        member = interaction.user
        channel = channel or bot_channel # type: ignore
        
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"You must send this command from, or set `channel` to, a text channel.", bot = self.bot), ephemeral = True) # type: ignore
            return

        channel_id = channel.id # type: ignore
        
        limits = get_user_role_limits(member) # type: ignore
        user_reminders = await reminders.get_user_reminder(member.id, repeating_only = (repeat != None)) # type: ignore
        
        if not channel.permissions_for(member).send_messages: # type: ignore
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"You must be able to send messages in the channel you set. Try a channel that isn't {channel.mention}", bot = self.bot), ephemeral = True) # type: ignore
            return
        
        if repeat and len(user_reminders) >= limits["repeat"]: # type: ignore
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"You have reached the maximum number of repeating reminders (`{limits["repeat"]}`).", bot = self.bot), ephemeral = True)
            return
        
        if not repeat and len(user_reminders) >= limits["non_repeat"]: # type: ignore
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"You have reached the maximum number of non-repeating reminders (`{limits["non_repeat"]}`).", bot = self.bot), ephemeral = True)
            return
        
        # Add reminder
        link = f"https://twemoji.maxcdn.com/v/latest/72x72/{ord("⌚"):x}.png"
        
        reminder_id = await reminders.add_reminder(member.id, future_timestamp, channel_id, message, repeat)
        await interaction.response.send_message(embed = basic_embed(title = "Reminder Set", description = f"Reminder set for {member.mention} \n> - **Time Set For**: <t:{future_timestamp}:F> (<t:{future_timestamp}:R>) \n> - **Message**: {message} \n> - **Repeats**: {repeat if repeat else "`N/A`"} \n> - **Channel**: {channel.mention} \n> - **Reminder ID**: `{reminder_id}`" , bot = self.bot, thumbnail = link)) # type: ignore
        
        self.wakeup.set()
    
    # /embed
    @app_commands.command(name = "embed", description = "Creates an embed using the bot.")
    @app_commands.describe(title = "The title of the embed", description = "The description of the embed, optional", color = "The color of the embed, like #1f1f1f, optional", image = "The image of the embbed, optional")
    async def embed(self, interaction: discord.Interaction, title: str, description: str = "", color: str = "", image: discord.Attachment | None = None):
        
        if color == "": rgb_color = DEFAULT_COLOR
        
        else: 
            
            try: rgb_color = discord.Color.from_rgb(*self.hex_to_rgb(self.parse_colors("[" + color + "]", max_colors = 1)[0]))
            
            except Exception as e:
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
                return
        
        img_binary = None
        
        try: img_binary = await get_icon_binary(image, max_kb = 51200, max_size = (1024, 1024))
        except ValueError as e: await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
    
        embed_image = io.BytesIO(img_binary) if img_binary else None
        embed_image_file = discord.File(embed_image, filename = "embed_image.png") if img_binary else None # type: ignore

        e = discord.Embed(title = title, description = description, color = rgb_color)
        e.set_author(name = interaction.user.name, icon_url = interaction.user.display_avatar.url) 

        if embed_image_file:
            
            e.set_image(url = "attachment://embed_image.png")
            await interaction.response.send_message(embed = e, file = embed_image_file)
        
        else:
            
          await interaction.response.send_message(embed = e)  
     
    # /convert
    @app_commands.command(name = "convert", description = "Convert anything to anything, powered by p2r3/convert.")
    @app_commands.describe(input = "The input file to convert", output = "The output format to convert to.")
    async def convert(self, interaction: discord.Interaction, input: discord.Attachment, output: str):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        limits = {BLOB_ROLE: (60, 10),
                  SUIT_ROLE: (60, 10),
                  SHADES_ROLE: (60, 10),
                  SHADES_PLUS_ROLE: (30, 10),
                  SHADES_PLUS_PLUS_ROLE: (30, 10),
                  CLASSY_ROLE: (30, 10),
                  CLASSY_PLUS_ROLE: (30, 1000),
                  MAX_CLASS_ROLE: (30, 1000),
                  SERVER_BOOSTER_ROLE: (30, 1000)}
        
        our_limits = (60, 10)
        
        converts_done = 0
        convert_reminder = -1
        
        tomorrow = datetime.now() + timedelta(days = 1)
        tmr_timestamp = int(tomorrow.timestamp())

        for role_id, limits_tup in limits.items():
            if role_id in [r.id for r in interaction.user.roles]: # type: ignore
                if our_limits[0] > limits_tup[0] or our_limits[1] < limits_tup[1]:
                    our_limits = copy(limits_tup)
        
        all_reminders = await reminders.get_due_reminders()   
            
        for (reminder_id, user_id, timestamp, repeat, channel_id, message) in all_reminders:
            
            if message: 
                
                if int(user_id) == int(BOT_ID) and message == f"cooldown:convert:{interaction.user.id}":
                    
                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"You have a cooldown to using this command until <t:{timestamp}:F> (<t:{timestamp}:R>).", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
                    return
                
                if int(user_id) == int(BOT_ID) and (message.split(':')[0] == 'usage') and (message.split(':')[1] == 'convert') and (message.split(':')[2] == str(interaction.user.id)):
                    
                    convert_reminder = reminder_id
                    converts_done = int(message.split(':')[3])                    
                    converts_left = our_limits[1] - converts_done
                    
                    if converts_left == 0:
                        
                        await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"You have no more conversions left today. Try again on <t:{tmr_timestamp}:D> (<t:{tmr_timestamp}:R>).", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
                        return
                    
        await interaction.response.defer()
        
        uid = str(uuid.uuid4())
        
        input_ext = input.filename.split('.')[-1]
        input_path = CONVERT_PATH + fr"\{uid}.{input_ext}"
        output_path = None
        
        try:
            
            await download_file(input.url, input_path)
            output_path = await asyncio.wait_for(run_docker_command(comm = "convert", input_path = input_path, output_ext = output.lower()), timeout = 60)
            
            file = discord.File(output_path)
            
            if os.path.getsize(output_path) > 45_000_000:
                raise Exception("The output file size is too large (over `45MB`).")

            await interaction.followup.send(file = file)
            
            converts_done += 1
            
            await reminders.add_reminder(BOT_ID, int(datetime.now().timestamp()) + our_limits[0], interaction.channel_id, message = f"cooldown:convert:{interaction.user.id}", repeat = None) # type: ignore
            
            if convert_reminder != -1: await reminders.delete_reminder(convert_reminder)
            await reminders.add_reminder(BOT_ID, tmr_timestamp, interaction.channel_id, message = f"usage:convert:{interaction.user.id}:{converts_done}", repeat = None) # type: ignore

            self.wakeup.set()
        
        except asyncio.TimeoutError:
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"The conversion took longer than `{60}` seconds and timed out.", bot = self.bot), ephemeral = True)
            return
        
        except Exception as e:
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
            return
        
        finally: cleanup(input_path, output_path)
              
    # /edit-image
    @app_commands.command(name = "edit-image", description = "Edit an image by adding some filters.")
    @app_commands.describe(input = "The input image to edit", value = "The value to operate on", operation = "What type of editing operation to do.")
    @app_commands.choices(operation = [app_commands.Choice(name = "Blur Image", value = "blur"),
                                       app_commands.Choice(name = "Sharpen Image", value = "sharpen"),
                                       app_commands.Choice(name = "Monochrome Image", value = "monochrome"),
                                       app_commands.Choice(name = "Invert Image", value = "invert"),
                                       app_commands.Choice(name = "Shift Hue of Image", value = "hue"),])
    async def edit_image(self, interaction: discord.Interaction, input: discord.Attachment, value: str, operation: app_commands.Choice[str]):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        limits = {BLOB_ROLE: (60, 10),
                  SUIT_ROLE: (60, 10),
                  SHADES_ROLE: (60, 10),
                  SHADES_PLUS_ROLE: (30, 10),
                  SHADES_PLUS_PLUS_ROLE: (30, 10),
                  CLASSY_ROLE: (30, 10),
                  CLASSY_PLUS_ROLE: (30, 1000),
                  MAX_CLASS_ROLE: (30, 1000),
                  SERVER_BOOSTER_ROLE: (30, 1000)}
        
        our_limits = (60, 10)
        
        edits_done = 0
        edit_reminder = -1
        
        tomorrow = datetime.now() + timedelta(days = 1)
        tmr_timestamp = int(tomorrow.timestamp())

        for role_id, limits_tup in limits.items():
            if role_id in [r.id for r in interaction.user.roles]: # type: ignore
                if our_limits[0] > limits_tup[0] or our_limits[1] < limits_tup[1]:
                    our_limits = copy(limits_tup)
        
        all_reminders = await reminders.get_due_reminders()   
            
        for (reminder_id, user_id, timestamp, repeat, channel_id, message) in all_reminders:
            
            if message: 
                
                if int(user_id) == int(BOT_ID) and message == f"cooldown:edit:{interaction.user.id}":
                    
                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"You have a cooldown to using this command until <t:{timestamp}:F> (<t:{timestamp}:R>).", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
                    return
                
                if int(user_id) == int(BOT_ID) and (message.split(':')[0] == 'usage') and (message.split(':')[1] == 'edit') and (message.split(':')[2] == str(interaction.user.id)):
                    
                    edit_reminder = reminder_id
                    edits_done = int(message.split(':')[3])                    
                    edits_left = our_limits[1] - edits_done
                    
                    if edits_left == 0:
                        
                        await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"You have no more edits left today. Try again on <t:{tmr_timestamp}:D> (<t:{tmr_timestamp}:R>).", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
                        return
                    
        await interaction.response.defer()
        
        uid = str(uuid.uuid4())
        
        input_ext = input.filename.split('.')[-1]
        
        if input_ext.lower() not in ["png", "jpg", "jpeg", "webp"]:
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"File type must be one of `png`, `jpg`, `jpeg` or `webp`.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return
            
        input_path = CONVERT_PATH + fr"\{uid}.{input_ext}"
        output_path = None
        
        try:
            
            await download_file(input.url, input_path)
            output_path = await asyncio.wait_for(run_docker_command(comm = "edit-image", input_path = input_path, output_ext = input_ext, operation = operation.value, value = value), timeout = 60)
            
            file = discord.File(output_path)
            
            if os.path.getsize(output_path) > 45_000_000:
                raise Exception("The output file size is too large (over `45MB`).")

            await interaction.followup.send(file = file)
            
            edits_done += 1
            
            await reminders.add_reminder(BOT_ID, int(datetime.now().timestamp()) + our_limits[0], interaction.channel_id, message = f"cooldown:edit:{interaction.user.id}", repeat = None) # type: ignore
            
            if edit_reminder != -1: await reminders.delete_reminder(edit_reminder)
            await reminders.add_reminder(BOT_ID, tmr_timestamp, interaction.channel_id, message = f"usage:edit:{interaction.user.id}:{edits_done}", repeat = None) # type: ignore

            self.wakeup.set()
        
        except asyncio.TimeoutError:
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"The edit took longer than `{60}` seconds and timed out.", bot = self.bot), ephemeral = True)
            return
        
        except Exception as e:
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
            return
        
        finally: cleanup(input_path, output_path)
            
    # /color
    @app_commands.command(name = 'color', description = "Show a hex color or gradient of sequence of colors.")
    @app_commands.describe(hexes = "Either a single hex like #0f0f0f, or formatted in a comma-separated list like [#0f0f0f,#1f1f1f]")
    async def color(self, interaction: discord.Interaction, hexes: str):

        try:

            hexes_list = self.parse_colors(hexes)
        
        except ValueError as e:

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
            return

        # Generate image file
        buffer = self.generate_color_image((512, 64), hexes_list)
        file = discord.File(buffer, filename = "color.png")

        # Generate embed
        e = discord.Embed(title = "Generated Color", color = discord.Color.from_rgb(*self.hex_to_rgb(hexes_list[0])), timestamp = datetime.now())
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

        counter = 1

        for h in hexes_list:
                
            e.add_field(name = f"Hex #{counter}", value = f"`#{h.lower()}`", inline = True)
            e.add_field(name = f"RGB", value = f"`{self.hex_to_rgb(h)}`", inline = True)
            e.add_field(name = "\u200b", value = "\u200b", inline = True)

            counter += 1

        e.set_image(url = await upload_asset(self.bot, file))
        await interaction.response.send_message(embed = e)

    # /roll
    @app_commands.command(name = 'roll', description = "Rolls some dice.")
    @app_commands.describe(sides = "Number of sides on a single die", advanced = "Advanced die notation like 24d32, d10*2 or 17d[8,13]")
    async def roll(self, interaction: discord.Interaction, sides: int = 6, advanced: str | None = None):
        
        MAX_DICE = 1000
        MAX_SIDES = 1_000_000_000

        def parse_advanced(query: str) -> dict: 
            
            query = query.replace(" ", "")

            # Match dice expression + optional math, like d7, 2d10, d10*2, 2d10*2+5, 17d[8,13]+3
            
            m = re.fullmatch(r"(\d*)d(\d+|\[(\d+),(\d+)\])((?:[*+]\d+)*)", query)

            if not m:

                raise ValueError("Invalid roll format. Examples: `d7`, `2d10`, `d10*2`, `2d10*2+5`, `17d[8,13]+3`.")
            
            dice_str = m.group(1)
            sides_str = m.group(2)
            min_s = m.group(3)
            max_s = m.group(4)
            
            math_part = m.group(5)

            n = int(dice_str) if dice_str else 1

            if not (1 <= n <= MAX_DICE):
                raise ValueError(f"Too many/few dice. Dice count must be between `{1}` and `{MAX_DICE}`.")

            if min_s:

                min_s = int(min_s)
                max_s = int(max_s)

                if (min_s < 1) or (max_s > MAX_SIDES) or (min_s > max_s):
                    raise ValueError(f"Invalid range. Range must fall between `{1}` and `{MAX_DICE}`, and the minimum must be less than the maximum.")

                rolls = np.random.randint(min_s, max_s + 1, size = n)
            
            else: # no range
                
                s = int(sides_str)

                if not (1 <= s <= MAX_SIDES):
                    raise ValueError(f"Sides must be between `{1}` and `{MAX_SIDES}`.")
                
                rolls = np.random.randint(1, s + 1, size = n)
            
            rolls_list = rolls.tolist()
            total = sum(rolls)

            multiplier = 1
            addition = 0

            try:

                for op, value in re.findall(r"([*+])(\d+)", math_part):
                            
                    value = int(value)

                    if op == "*": multiplier *= value
                    elif op == "+": addition += value
                    elif op == "-": addition -= value
                    
                final_value = total * multiplier + addition

                return {"rolls": rolls_list, "sum": total, "multiplier": multiplier, "addition": addition, "final": final_value, "notation": query}

            except OverflowError:

                raise ValueError("The final value, or one of the intermediary steps, overflowed the C long limit.")

        if not sides and not advanced:
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = "You must provide at least one argument: `sides` or `advanced`.", bot = self.bot), ephemeral = True)
            return

        results = {}
        
        if advanced: # advanced overriding sides

            try:
                results = parse_advanced(advanced)

            except ValueError as e:
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
                return

        else:

            if not (1 <= sides <= MAX_SIDES): # type: ignore
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"`sides` must be between `1` and `{MAX_SIDES}`.", bot = self.bot), ephemeral = True)
                return
            
            roll_result = np.random.randint(low = 1, high = sides + 1) # type: ignore
            results = {"rolls": [roll_result]}


        # Format output
        if len(results["rolls"]) > 50:
            description = f"Rolled **{len(results["rolls"])}** dice. Showing first 50: `{results["rolls"][:50]}`"
        
        else:
            description = f"Rolled **{len(results["rolls"])}** dice: `{results["rolls"]}`"
        
        if not advanced:
            description += f"\nSides: `{sides}`"

        else:
        
            if len(results["rolls"]) > 50:
                description = f"Rolled **{len(results["rolls"])}** dice. Showing first 50: `{results["rolls"][:50]}`"
            
            else:
                description = f"Rolled **{len(results["rolls"])}** dice: `{results["rolls"]}`"
                
            description += f"\n> - Sum: `{results["sum"]}`\n> - Multiplier: `{results["multiplier"]}`\n> - Addition: `{results["addition"]}`\n> - **Final Value**: `{results["final"]}`\n> - **Query**: `{results["notation"]}`" # type: ignore
        
        # Add emoji
        codepoint = f"{ord("🎲"):x}"
        link = f"https://twemoji.maxcdn.com/v/latest/72x72/{codepoint}.png"

        results_embed = basic_embed(title = "Dice Roll",
                                    description = description,
                                    bot = self.bot,
                                    thumbnail = link)
        
        await interaction.response.send_message(embed = results_embed)

    # / introduce
    @app_commands.command(name = "introduce", description = "A temporary command allowing one to edit their introduction.")
    async def introduce(self, interaction: discord.Interaction):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        member = interaction.user # type: ignore
        
        class IntroductionModal(discord.ui.Modal):
            
            def __init__(self, bot, wakeup: asyncio.Event):
                
                super().__init__(title = "Introduction Form")
                
                self.add_item(discord.ui.TextInput(label = "About Me", placeholder = "Enter your introdution text here...", style = discord.TextStyle.paragraph))
                self.add_item(discord.ui.TextInput(label = "Birthday", placeholder = "Your birthday in format (DD-MM), eg. 24-07 (optional)", required = False))
                self.add_item(discord.ui.TextInput(label = "Country", placeholder = "Copypaste a Unicode country emoji into here... (optional)", required = False))

                self.bot = bot
                self.wakeup = wakeup
            
            def next_date(self, dt):
                
                try:
                    
                    today = datetime.today()
                    target = datetime(year = today.year, month = dt.month, day = dt.day) # type: ignore
                
                except:
                    
                    raise ValueError("Invalid day/month combination.")
                
                if target <= today:
                    target = datetime(year = today.year + 1, month = dt.month, day = dt.day) # type: ignore
                
                return target
                
            async def on_submit(self, interaction: discord.Interaction):
                
                about_me = self.children[0].value # type: ignore
                birthday = self.children[1].value # type: ignore
                country = self.children[2].value # type: ignore
                
                try:
                    
                    if birthday: 
                        try: _date = datetime.strptime(birthday, "%d-%m") 
                        except ValueError: raise AssertionError(f"`date` is not a valid date")
                    
                    else: _date = 0
                    
                    if country: assert emoji.is_emoji(country), f"`country` is not is not an emoji"
                
                except AssertionError as e:
                    
                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
                    return

                if _date: target_date = int(self.next_date(_date).timestamp())
                else: target_date = None

                await users.set_user_intro(member.id, about_me, target_date, country)
                await interaction.response.send_message(embed = basic_embed(title = "Introduction Form", description = f"Introduction set.", bot = self.bot), ephemeral = True)
                    
        await interaction.response.send_modal(IntroductionModal(bot = self.bot, wakeup = self.wakeup))
        
    # /bot-status 
    @app_commands.command(name = "bot-status", description = "Shows information about the bot.")
    @app_commands.describe(graph = "Whether to generate a live graph of metrics, optional")
    async def botstatus(self, interaction: discord.Interaction, graph: bool = False):
        
        if graph and not is_moderator(interaction.user): # type: ignore
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Using the `graph` argument is a permission for {guild.get_role(MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return

        async def run_graph_updates(message: discord.Message):
            
            cpu_data, mem_data, net_data, time_data = [], [], [], []
            
            peak_cpu = 0
            peak_mem = 0
            peak_net = 0
            
            prev_net = psutil.net_io_counters()
            
            for i in range(720):
                
                cpu = self.process.cpu_percent(interval = None) # type: ignore
                mem = self.process.memory_percent() # type: ignore
                
                current_net = psutil.net_io_counters()
                
                delta_bytes = ((current_net.bytes_sent - prev_net.bytes_sent) + (current_net.bytes_recv - prev_net.bytes_sent))
                
                if i == 0:
                    net_usage = 0
                
                else:
                    
                    if delta_bytes < 0 or delta_bytes > 100 * 1024 * 1024: net_usage = 0
                    else: net_usage = delta_bytes / 1024 / 5
                
                current_net = prev_net

                cpu_data.append(cpu)
                mem_data.append(mem)
                net_data.append(net_usage)
                time_data.append(i * 5)
                
                cpu_data = cpu_data[-30:]
                mem_data = mem_data[-30:]
                net_data = net_data[-30:]
                time_data = time_data[-30:]
                
                peak_cpu = max(peak_cpu, cpu)
                peak_mem = max(peak_mem, mem)
                peak_net = max(peak_net, net_usage)
                
                buffer = make_graph(time_data, cpu_data, mem_data, net_data)
                file = discord.File(buffer, filename = "botstats.png")
                
                e = discord.Embed(title = "Bot Status", color = DEFAULT_COLOR, timestamp = datetime.now())
                e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

                e.description = f"""An open source Discord bot, written to power The Toblobs Lounge.\n## __Bot Information__
        > - **Current Version**: `v{VERSION}` (last updated <t:1774051200:R>)
        > - **Codebase**: {GITHUB_LINK}
        > - **Documentation & Help**: *Coming soon...*
        ## __Program Information__
        > - **Uptime**: `{self.get_uptime()}`    
        """
                e.add_field(name = "Current", value = f"> - **CPU**: `{cpu:.1f}%`\n> - **Memory**: `{mem:.1f}%`\n> - **Network**: `{int(net_usage)} KB/s`")
                e.add_field(name = "Peak (5 min)", value = f"> - **CPU**: `{peak_cpu:.1f}%`\n> - **Memory**: `{peak_mem:.1f}%`\n> - **Network**: `{int(peak_net)} KB/s`")

                e.set_image(url = "attachment://botstats.png")
                
                await message.edit(embed = e, attachments = [file])
                
                await asyncio.sleep(5)
        
        def make_graph(time_data, cpu_data, mem_data, net_data):
               
            fig, ax = plt.subplots()
            
            ax.plot(time_data, cpu_data, label = "CPU %")
            ax.plot(time_data, mem_data, label = "Memory %")
            #ax.plot(time_data, net_data, label = "Network KB/(5s)")
            
            plt.xlabel("Time (seconds)")
            plt.ylabel("Usage")

            fig.patch.set_facecolor("#1a1a1e")
            ax.set_facecolor("#1a1a1e")

            ax.xaxis.label.set_color("white")
            ax.yaxis.label.set_color("white")

            ax.tick_params(axis = "both", colors = "white")
        
            ax.grid(axis = "x", linestyle = "--", alpha = 0.2, color = "white")
            ax.grid(axis = "y", linestyle = "--", alpha = 0.2, color = "white")

            legend = ax.legend(framealpha = 0, frameon = False, labelcolor = "white", fontsize = 10, loc = "upper right")

            for spine in ax.spines.values():
                spine.set_color("white")
            
            ax.yaxis.set_major_locator(MaxNLocator(integer = True))
            ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))

            plt.tight_layout()
        
            buffer = io.BytesIO()
            plt.savefig(buffer, format = "png")
            plt.close()
            
            buffer.seek(0)
            
            plt.close()
            
            return buffer
        
        await interaction.response.defer()
        
        self.process = psutil.Process(os.getpid())

        uptime = self.get_uptime()
        
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent
        
        # Generate embed
        e = discord.Embed(title = "Bot Status", color = DEFAULT_COLOR, timestamp = datetime.now())
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore
        
        e.description = f"""An open source Discord bot, written to power The Toblobs Lounge.\n## __Bot Information__
        > - **Current Version**: `v{VERSION}` (last updated <t:1774051200:R>)
        > - **Codebase**: {GITHUB_LINK}
        > - **Documentation & Help**: *Coming soon...*
        ## __Program Information__
        > - **Uptime**: `{uptime}`    
        """
        
        message = (await interaction.followup.send(embed = e))
        if graph: asyncio.create_task(run_graph_updates(message)) # type: ignore