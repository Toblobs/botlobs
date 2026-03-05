# cogs > general.py // @toblobs // 05.03.26

from datetime import timedelta
from .__init__ import *

import re
import io
import time

from typing import List, Tuple

from discord import TextChannel, app_commands
from discord.ext import commands

import numpy as np
from PIL import Image
import emoji

from cogs.utils.embeds import basic_embed
from cogs.utils.permissions import *

from database import xp

class GeneralCommands(commands.Cog):

    def __init__(self, bot: commands.Bot):

        self.bot = bot

    ### generally used submodules

    def hex_to_rgb(self, hex: str) -> tuple:

            if hex[0] == '#': 
                stripped = hex.lstrip('#')
                
            else: 
                stripped = hex

            return tuple(int(stripped[i: i + 2], 16) for i in (0, 2, 4))

    def generate_color_image(self, size: Tuple[int, int], hexes_list: List[str]) -> io.BytesIO:

        img = Image.new("RGB", size)
        pixels = img.load()

        colors = [self.hex_to_rgb(h) for h in hexes_list]
        segments = len(colors) - 1

        for x in range(size[0]):

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
    
    ### commands

    # /help

    # /about
    @app_commands.command(name = "about", description = "Shows the info page for the server.")
    async def about(self, interaction: discord.Interaction):
        
        INVITE_CODE = "X53PzUqAvK"
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        banner = guild.banner # type: ignore

        information = {"🆔 **Server ID**": f"`{GUILD_ID}`", "<:toblobsjumpscare:1478176349876125909> **Owner**": f"{self.bot.get_user(762238670656634921).mention}", "<:blob:1478172385638350858> **Members**": f"`{sum(1 for m in guild.members if not m.bot)}`", # type: ignore
                       "⭐ **Created At**": f"<t:{int(guild.created_at.timestamp())}:D>", "🎆 **Opened At**": f"<t:1695164400:D>", "<:serverboosters:1478172421403054171> **Boost Level**": f"Level `{guild.premium_tier}` (`{guild.premium_subscription_count}` Boosts)", # type: ignore
                       "<:blacktie:1478172419113091143> **Roles**": f"`{len(guild.roles)}`", "📚 **Categories**": f"`{len([c for c in guild.channels if isinstance(c, discord.CategoryChannel)])}`", "👪 **Default Role**": f"{guild.get_role(1139122746199134249).mention}", # type: ignore
                       "💬 **Text Channels**": f"`{len([c for c in guild.channels if isinstance(c, discord.TextChannel)])}`", "🎧 **Voice Channels**": f"`{len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])}`", "➡️ **This Channel**": f"{interaction.channel.mention}", # type: ignore
                       "<:toblobsconfident:1478176334651064444> **Emojis**": f"`{len(guild.emojis)}`", "<:tobhead:1478172412494479380> **Bots**": f"`{sum(1 for m in guild.members if m.bot)}`", "📢 Invite Code:": f"https://discord.com/invite/{INVITE_CODE}", # type: ignore
        }

        e = discord.Embed(title = "The Toblobs Lounge: About Page", color = DEFAULT_COLOR, timestamp = datetime.now())
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

        for name, data in information.items(): e.add_field(name = name, value = data, inline = True)

        if banner:
            e.add_field(name = "**Server Banner**:", value = "\u200b")
            await e.set_image(url = banner.url) # type: ignore

        e.set_thumbnail(url = self.bot.user.display_avatar.url) # type: ignore
        await interaction.response.send_message(embed = e)

    # /info
    @app_commands.command(name = "info", description = "Shows the info page for a server member.")
    async def info(self, interaction: discord.Interaction, member: discord.Member | None = None):

        member = member or interaction.user # type: ignore

        if not member: 

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not fetch info about this member.", bot = self.bot), ephemeral = True)
            return

        information = {"mention": f"{member.mention}", "name": f"`{member.name}`", "id": f"`{member.id}`",
                       "joined": f"<t:{int(member.joined_at.timestamp())}:D> (<t:{int(member.joined_at.timestamp())}:R>)", "registered": f"<t:{int(member.created_at.timestamp())}:D> (<t:{int(member.created_at.timestamp())}:R>)", # type: ignore
                       "roles": member.roles, "permissions": [], "acknowledgments": [], "thumbnail": ""} 

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

        e.set_thumbnail(url = information["thumbnail"])
        await interaction.response.send_message(embed = e)

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

            if role.secondary_color:
                information["hexes"].append(f"#{role.secondary_color.value:06X}") # type: ignore

            if role.tertiary_color:
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

            e.set_thumbnail(url = information["thumbnail"])

            if file: e.set_image(url = await upload_asset(self.bot, file))
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

    # /remind

    # /convert

    # /color
    @app_commands.command(name = 'color', description = "Show a hex color or gradient of sequence of colors.")
    @app_commands.describe(hexes = "Either a single hex like #0f0f0f, or formatted in a comma-separated list like [#0f0f0f,#1f1f1f]")
    async def color(self, interaction: discord.Interaction, hexes: str):
        
        MAX_COLORS = 8

        def parse_colors(text: str) -> List[str]:
            
            HEX_PATTERN = re.compile(r"^#?([0-9A-Fa-f]{6})$")
            
            text = text.strip()

            if HEX_PATTERN.match(text):
                
                return [HEX_PATTERN.match(text).group(1).upper()] # type: ignore

            if text.startswith('[') and text.endswith(']'):

                inner = text[1:-1]

                parts = [p.strip() for p in inner.split(",")]

                if len(parts) == 0:
                    raise ValueError("Empty color sequence.")
                
                if len(parts) > MAX_COLORS:
                    raise ValueError(f"`{len(parts)}` colors provided, the maximum is `{MAX_COLORS}` colors.")
                
                colors = []

                for p in parts:
                    
                    m = HEX_PATTERN.match(p)

                    if not m:
                        raise ValueError(f"Invalid hex color: `{p}`.")
                    
                    colors.append(m.group(1).upper())
                
                return colors

            raise ValueError("Invalid format: use either `RRGGBB` or `[RRGGBB, RRGGBB, ...]`.")

        try:

            hexes_list = parse_colors(hexes)
        
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

                raise ValueError("Invalid format. Examples: `d7`, `2d10`, `d10*2`, `2d10*2+5`, `17d[8,13]+3`.")
            
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