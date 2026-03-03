# cogs > general.py // @toblobs // 02.03.26

from __init__ import *

import re
import io

from typing import List, Tuple

from discord import app_commands
from discord.ext import commands

import numpy as np
from PIL import Image

from cogs.utils.embeds import basic_embed


class GeneralCommands(commands.Cog):

    def __init__(self, bot: commands.Bot):

        self.bot = bot

    @app_commands.command(name = "about", description = "Shows the info page for the server.")
    async def about(self, interaction: discord.Interaction):
        
        INVITE_CODE = "X53PzUqAvK"
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        banner = guild.banner # type: ignore

        information = {"🆔 **Server ID**": f"`{GUILD_ID}`", "<:toblobsjumpscare:1478176349876125909> **Owner**": f"{self.bot.get_user(762238670656634921).mention}", "<:blob:1478172385638350858> **Members**": f"`{sum(1 for m in guild.members if not m.bot)}`", # type: ignore
                       "⭐ **Created At**": f"<t:{int(guild.created_at.timestamp())}:D>", "🎆 **Opened At**": f"<t:1695164400:D>", "<:serverboosters:1478172421403054171> **Boost Level**": f"Level `{guild.premium_tier}` (`{guild.premium_subscription_count}` Boosts)", # type: ignore
                       "<:blacktie:1478172419113091143> **Roles**": f"`{len(guild.roles)}`", "📚 **Categories**": f"`{len([c for c in guild.channels if isinstance(c, discord.CategoryChannel)])}`", "👪 **Default Role**": f"{guild.get_role(1139122746199134249).mention}", # type: ignore
                       "💬 **Text Channels**": f"`{len([c for c in guild.channels if isinstance(c, discord.TextChannel)])}`", "🎧 **Voice Channels**": f"`{len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])}`", "➡️ **This Channel**": f"{interaction.channel.mention}", # type: ignore
                       "<:toblobsconfident:1478176334651064444> **Emojis**": f"`{len(guild.emojis)}`", "<:tobhead:1478172412494479380> **Bots**": f"`{sum(1 for m in guild.members if m.bot)}`", "📢 Invite Code:": f"https://discord.com/invite/{INVITE_CODE}"} # type: ignore

        e = discord.Embed(title = "The Toblobs Lounge: About Page", color = DEFAULT_COLOR, timestamp = datetime.now())
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

        for name, data in information.items(): e.add_field(name = name, value = data, inline = True)

        if banner:
            e.add_field(name = "**Server Banner**:", value = "\u200b")
            await e.set_image(url = banner.url) # type: ignore

        e.set_thumbnail(url = self.bot.user.display_avatar.url) # type: ignore
        await interaction.response.send_message(embed = e)

    @app_commands.command(name = "ping", description = "Tests the bot's latency.")
    async def ping(self, interaction: discord.Interaction):
        
        time_taken = (interaction.created_at - datetime.now(timezone.utc)).microseconds / 1000

        await interaction.response.send_message(embed = basic_embed(title = "Pong!", description = f"Responded in `{time_taken}` ms.", bot = self.bot))

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


        # format output
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
        
        results_embed = basic_embed(title = "Dice Roll",
                                    description = description,
                                    bot = self.bot
                                    )
        
        await interaction.response.send_message(embed = results_embed)

    @app_commands.command(name = 'color', description = "Show a hex color or gradient of sequence of colors.")
    @app_commands.describe(hexes = "Either a single hex like #0f0f0f, or formatted in a comma-separated list like [#0f0f0f,#1f1f1f]")
    async def color(self, interaction: discord.Interaction, hexes: str):
        
        MAX_COLORS = 8

        def hex_to_rgb(hex: str) -> tuple:

            if hex[0] == '#': 
                stripped = hex.lstrip('#')
                
            else: 
                stripped = hex

            return tuple(int(stripped[i: i + 2], 16) for i in (0, 2, 4))

        def generate_color_image(size: Tuple[int, int], hexes_list: List[str]) -> io.BytesIO:

            img = Image.new("RGB", size)
            pixels = img.load()

            colors = [hex_to_rgb(h) for h in hexes_list]
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

        # generate image file
        buffer = generate_color_image((512, 64), hexes_list)
        file = discord.File(buffer, filename = "color.png")

        # generate embed
        e = discord.Embed(title = "Generated Color", color = discord.Color.from_rgb(*hex_to_rgb(hexes_list[0])), timestamp = datetime.now())
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

        counter = 1

        for h in hexes_list:
                
            e.add_field(name = f"Hex #{counter}", value = f"`#{h.lower()}`", inline = True)
            e.add_field(name = f"RGB", value = f"`{hex_to_rgb(h)}`", inline = True)
            e.add_field(name = "\u200b", value = "\u200b", inline = True)

            counter += 1

        e.set_image(url = "attachment://color.png")
        await interaction.response.send_message(embed = e, file = file)