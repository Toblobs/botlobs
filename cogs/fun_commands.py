# cogs > fun_commands.py // @toblobs // 21.03.26

from datetime import timedelta
from zoneinfo import ZoneInfo
import time
from .__init__ import *
import ast

import re
import io
import asyncio
import math
import aiohttp
import textwrap

from typing import List, Tuple

from discord import app_commands
from discord.ext import commands
from discord.utils import remove_markdown, escape_mentions

import numpy as np
import random

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from PIL import Image, ImageDraw, ImageFont

from cogs import get_top_colored_role, upload_asset
from cogs.utils.embeds import basic_embed
from cogs.utils.permissions import *
from cogs.utils.music import *

from database import reminders, quotes

async def send_qotd(bot, guild, channel):
    
    pool: list = list(await quotes.get_all_quotes()) or []
        
    (quote_id, user_id, message_id, content, timestamp) = random.choice(pool)
    
    quote_author = guild.get_member(user_id) # type: ignore

    # Get avatar
    async with aiohttp.ClientSession() as session:
        async with session.get(quote_author.display_avatar.url) as resp: # type: ignore
            avatar_bytes = await resp.read()
            
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = avatar.resize((128, 128))
    
    # Generate quote image
    img = Image.new("RGBA", (900, 300), (54, 57, 63))
    draw = ImageDraw.Draw(img)
    
    try: font = ImageFont.truetype("fonts/arial.ttf", 36)
    except: font = ImageFont.load_default(size = 36)
    
    try: small_font = ImageFont.truetype("fonts/arial.ttf", 18)
    except: small_font = ImageFont.load_default(size = 18)
    
    wrapped = textwrap.fill(content, width = 30)
    draw.text((200, 80), f'{wrapped}', font = font, fill = "white")
    
    date = datetime.fromtimestamp(int(timestamp))
    footer = f"— {quote_author.name}, {date.strftime("%b %d %Y")} | Quote ID: {quote_id}" # type: ignore
    draw.text((200, 200), footer, font = small_font, fill = (200, 200, 200))
    
    img.paste(avatar, (40, 80), avatar)
    
    buffer = io.BytesIO()
    img.save(buffer, "PNG")
    buffer.seek(0)
    
    file = discord.File(buffer, filename = "member_quote.png")

    e = discord.Embed(title = f"Member Quote", color = DEFAULT_COLOR, timestamp = datetime.now())
    e.set_author(name = f"BotLobs", icon_url = bot.user.display_avatar.url) # type: ignore
    
    e.set_image(url = await upload_asset(bot, file))
    await channel.send(embed = e)
            
class FunCommands(commands.Cog):
    
    def __init__(self, bot: commands.Bot, wakeup: asyncio.Event):

        self.bot = bot
        self.wakeup = wakeup
        
        self.recent_news_cache = []
        self.last_news_fetch = datetime(2026, 1, 1)
        
        self.live_tierlists = {}
        
        self.sp = spotipy.Spotify(auth_manager = SpotifyClientCredentials(client_id = SPOTIFY_ID, client_secret = SPOTIFY_SECRET))

    ### generally used submodules
    def normalize_image(self, img: Image.Image, constants):
            
        img = img.convert("RGBA")
        img.thumbnail((constants["tile-size"], constants["tile-size"]))
        
        canvas = Image.new("RGBA", (constants["tile-size"], constants["tile-size"]), (0, 0, 0, 0))
        
        x = (constants["tile-size"] - img.width) // 2
        y = (constants["tile-size"] - img.height) // 2
        
        canvas.paste(img, (x, y), img)
        return canvas
    
    def compute_canvas_size(self, tiers, constants):
            
            width = constants["label-width"] + (constants["max-per-row"] * constants["tile-size"]) + 2
            height = 2 * len(tiers) # start with margins
            
            for tier in tiers:
                
                count = len(tier["images"])
                rows = max(1, math.ceil(count / constants["max-per-row"]))
                
                tier_height = rows * constants["tile-size"]
                height += tier_height
                
                tier["rows"] = rows
                tier["height"] = tier_height
                
            return width, height
        
    def compute_label_width(self, tiers, font, base_width = 180, padding = 40):

        dummy_img = Image.new("RGB", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        
        max_text_width = 0
        
        for tier in tiers:
            text = tier["name"]
            
            bbox = draw.textbbox((0, 0), text, font = font)
            text_width = bbox[2] - bbox[0]
            
            max_text_width = max(max_text_width, text_width)
        
        return max(base_width, max_text_width + padding) 
        
    def render_tierlist(self, tiers, constants):
            
        try: font = ImageFont.truetype("fonts/arial.ttf", 48)
        except: font = ImageFont.load_default()
        
        constants["label-width"] = self.compute_label_width(tiers, font)
        width, height = self.compute_canvas_size(tiers, constants)
        
        canvas = Image.new("RGBA", (width, height), constants["bg-color"])
        draw = ImageDraw.Draw(canvas)
        
        current_y = 0
        
        for tier in tiers:
                
            tier_color = "#" + tier["color"]
            tier_height = tier["height"]
            
            # Draw label background
            draw.rectangle((0, current_y, constants["label-width"], current_y + tier_height), fill = tier_color)
            
            # Draw text
            text = tier["name"]
            text_w, text_h = draw.textbbox((0, 0), text, font = font)[2:]
            
            text_x = (constants["label-width"] - text_w) // 2
            text_y = current_y + (tier_height - text_h) // 2
                
            draw.text((text_x, text_y), text, fill = "black", font = font)
            
            for i, img in enumerate(tier["images"]):

                row = i // constants["max-per-row"]
                col = i % constants["max-per-row"]
                
                x = constants["label-width"] + col * constants["tile-size"] + 2
                y = current_y + row * constants["tile-size"]
                
                canvas.paste(img, (x, y))
            
            draw.line((constants["label-width"], current_y, constants["label-width"], current_y + tier_height), fill = (0, 0, 0), width = 2)
            draw.line((0, current_y + tier_height, width, current_y + tier_height), fill = (0, 0, 0), width = 2)
            current_y += tier_height + 2
        
        return canvas
    
    ### commands
    
    # /topic
    @app_commands.command(name = "topic", description = "Suggest a topic to talk about.")
    @app_commands.describe(category = "The category of topic to find, some will involve API calls")
    @app_commands.choices(category = [app_commands.Choice(name = "Random Category", value = "any"),
                                      app_commands.Choice(name = "Algodoo", value = "algodoo"),
                                      app_commands.Choice(name = "Art and Creativity", value = "art"),
                                      app_commands.Choice(name = "Music", value = "music"),
                                      app_commands.Choice(name = "Writing and Books", value = "writing"),
                                      app_commands.Choice(name = "Sports", value = "sport"),
                                      app_commands.Choice(name = "Video Games", value = "games"),
                                      app_commands.Choice(name = "Movies", value = "movies"),
                                      app_commands.Choice(name = "Trivia", value = "trivia"),
                                      app_commands.Choice(name = "Technology", value = "technology"),
                                      app_commands.Choice(name = "News", value = "news"),])                                             
    async def topic(self, interaction: discord.Interaction, category: app_commands.Choice[str] = "any"): # type: ignore
        
        await interaction.response.defer()
        
        async def get_news_topic() -> dict:
            
            time_diff_cooldown = (datetime.now() - self.last_news_fetch).seconds < 21600 # 6 hours cooldown
            
            if not time_diff_cooldown or not self.recent_news_cache:
                
                url = "https://newsapi.org/v2/top-headlines"
                params = {"pageSize": 20, "apiKey": NEWS_API, "language": "en"}
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params = params) as resp:
                        data = await resp.json()
                        
                self.recent_news_cache = data.get("articles", [])
            
            if self.recent_news_cache:
                
                article = random.choice(self.recent_news_cache)
                return {"title": article["title"], "source": article["source"]["name"], "url": article["url"]}
                
            else:
                
                return {"title": "No news articles found.", "source": "", "url": ""}
                
        async def get_embed_details(val: str) -> str:
            
            questions = {"algodoo": ["Who has been the best algotuber in the last year?"], 
                         "art": ["Who here can draw a duck fastest? Who would be the slowest?"], 
                         "music": ["What two artists would you really like to see a collaboration between?"], 
                         "writing": ["Worst part of the last book that you read?"], 
                         "sports": ["Who is winning the Champions Leauge this/next year?"], 
                         "games": ["What's the last game that you played on the Toblobs 20 Most Iconic list?"], 
                         "movies": ["Scariest horror movie that you watched as a child?"], 
                         "trivia": ["Name three different capitals of the five major continents."], 
                         "technology": ["What's one challenge you would be able to beat current-gen AI on?"]}
            
            match val:
                
                case "any":
                    
                    new_val = random.choice(["algodoo", "art", "music", "writing", "sport", "games", "movies", "trivia", "technology", "news"])
                    return await get_embed_details(new_val)
                    
                case "news":
                    
                    article = await get_news_topic()
                    return f"## Topic: News\n> - **Article Title**: {article["title"]}\n> - **Article Source**: {article["source"]}\n> - **Article URL**: {article["url"]}"
            
                case _:
                    
                    q = random.choice(questions[val])
                    return f"## Topic: {val.title()}\n> - **Question**: {q}"
        
        if category != "any": value = category.value
        else: value = "any"

        description = await get_embed_details(value) 
        await interaction.followup.send(embed = basic_embed(title = "Topic for Discussion", description = description, bot = self.bot))
        
    # /two-o-four-eight
    @app_commands.command(name = "two-o-four-eight", description = "Play a game of 2048.")
    async def two_o_four_eight(self, interaction: discord.Interaction):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        member = interaction.user # type: ignore
        
        # Cooldown permissions
        cooldown = {BLOB_ROLE: 10800, SHADES_ROLE: 3600, MAX_CLASS_ROLE: 600, SERVER_BOOSTER_ROLE: 600}
        our_cooldown = 10800
        
        for role in [guild.get_role(r) for r in [BLOB_ROLE, SHADES_ROLE, MAX_CLASS_ROLE, SERVER_BOOSTER_ROLE]]: # type: ignore
            if role in member.roles or is_at_least_level(member, role.id): # type: ignore
                our_cooldown = cooldown[role.id] # type: ignore
        
        all_reminders = await reminders.get_due_reminders()        
        for (reminder_id, user_id, timestamp, repeat, channel_id, message) in all_reminders:
            
            if int(user_id) == int(BOT_ID) and message == f"cooldown:2048:{member.id}":
                
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"You have a cooldown to using this command until <t:{timestamp}:F> (<t:{timestamp}:R>).", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore)
                return
            
        await reminders.add_reminder(BOT_ID, int(datetime.now().timestamp()) + our_cooldown, interaction.channel_id, message = f"cooldown:2048:{member.id}", repeat = None) # type: ignore
        self.wakeup.set()
        
        # Game constants
        WIDTH = 4
        HEIGHT = 4
        TILE_SIZE = 120
        PADDING = 15
        GRID_SIZE = 4
        
        BOARD_COLOR = (187, 173, 160)
        EMPTY_TILE = (205, 193, 180)
        
        TILE_COLORS = {
            1: (238, 228, 218),
            2: (237, 224, 200),
            3: (242, 177, 121),
            4: (245, 149, 99),
            5: (246, 124, 95),
            6: (246, 94, 59),
            7: (237, 207, 114),
            8: (237, 204, 97),
            9: (237, 200, 80),
            10: (237, 197, 63),
            11: (237, 194, 46),
        }
        
        start = int(datetime.now().timestamp())
        
        class Game2048:
            
            def __init__(self):
                
                self.board = [0] * (WIDTH * HEIGHT)
                self.score = 0
                self.merged = []
                
                # Start with 2 random squares
                for x in range(2): self.place_random()

            def index(self, x, y):
                return y * WIDTH + x
            
            def get(self, x, y):
                return self.board[self.index(x, y)]
            
            def set(self, x, y, value):
                self.board[self.index(x, y)] = value
                
            def place_random(self):
                
                empty = [i for i, v in enumerate(self.board) if v == 0]
                if not empty: return
                i = random.choice(empty)
                self.board[i] = 2 if random.random() < 0.25 else 1
            
            def compress_line(self, line):
                
                new = [i for i in line if i != 0]
                
                i  = 0
                while i < len(new) - 1:
                    
                    if new[i] == new[i + 1]:
                        new[i] += 1
                        self.score += 2 ** new[i]
                        new.pop(i + 1)
                    
                    i += 1 
                
                return new + [0] * (WIDTH - len(new))
            
            def move_left(self):
                
                moved = False
                
                for y in range(HEIGHT):
                    
                    row = [self.get(x, y) for x in range(WIDTH)]
                    new_row = self.compress_line(row)
                    
                    if row != new_row: moved = True
                    for x in range(WIDTH): self.set(x, y, new_row[x])
                
                return moved
            
            def move_right(self):
                
                moved = False
                
                for y in range(HEIGHT):
                    
                    row = [self.get(x, y) for x in reversed(range(WIDTH))]
                    new_row = self.compress_line(row)
                    new_row.reverse()
                    
                    if row[::-1] != new_row[::-1]: moved = True
                    for x in range(WIDTH): self.set(x, y, new_row[x])
                
                return moved
            
            def move_up(self):
                
                moved = False
                
                for x in range(WIDTH):
                    
                    col = [self.get(x, y) for y in range(HEIGHT)]
                    new_col = self.compress_line(col)
                    
                    if col != new_col: moved = True
                    for y in range(HEIGHT): self.set(x, y, new_col[y])
                
                return moved
            
            def move_down(self):
                
                moved = False
                
                for x in range(WIDTH):
                    
                    col = [self.get(x, y) for y in reversed(range(HEIGHT))]
                    new_col = self.compress_line(col)
                    new_col.reverse()
                    
                    if col[::-1] != new_col[::-1]: moved = True
                    for y in range(HEIGHT): self.set(x, y, new_col[y])
                
                return moved
            
            def is_game_over(self):
                
                if 0 in self.board: return False
                
                # Check for merges
                for y in range(HEIGHT):
                    for x in range(WIDTH):
                        v = self.get(x, y)
                        for dx, dy in [(1, 0), (0, 1)]:
                            nx, ny = x + dx, y + dy
                            if nx  < WIDTH and ny < HEIGHT:
                                if self.get(nx, ny) == v:
                                    return False
                                
                return True
        
        def get_font(size):
            
            try: font = ImageFont.truetype("fonts/arial.ttf", size)
            except: font = ImageFont.load_default()
            
            return font
        
        def get_tile_color(value):
            
            if value in TILE_COLORS: return TILE_COLORS[value]
            return (237, max(150, 194 - value * 2), 46)
        
        def get_font_color(value):
            
            if value in [1, 2]: return (113, 104, 97)
            else: return (249, 246, 239)
            
        def get_font_size(value):
            
            digits = len(str(2 ** value))
            
            match digits:
                
                case 1: return 48
                case 2: return 48
                case 3: return 40
                case 4: return 32
                case _: return 24
               
        def draw_board(board):
            
            size = GRID_SIZE * TILE_SIZE + (GRID_SIZE + 1) * PADDING
            img = Image.new("RGB", (size, size), BOARD_COLOR)
            draw = ImageDraw.Draw(img)
            
            for y in range(GRID_SIZE):
                for x in range(GRID_SIZE): 
                    
                    value = board[y * GRID_SIZE + x]
                    
                    px = PADDING + x * (TILE_SIZE + PADDING)
                    py = PADDING + y * (TILE_SIZE + PADDING)
                    
                    if value == 0: color = EMPTY_TILE
                    else: color = get_tile_color(value)
                    
                    draw.rounded_rectangle((px, py, px + TILE_SIZE, py + TILE_SIZE), radius = 12, fill = color)
                    
                    if value != 0:
                    
                        text = str(2 ** value)
                        font_size = get_font_size(value)  
                        font_color = get_font_color(value)                      
                        font = get_font(font_size)
                        

                        bbox = draw.textbbox((0, 0), text, font = font)
                        tw = bbox[2] - bbox[0]
                        th = bbox[3] - bbox[1]
                        
                        draw.text((px + TILE_SIZE / 2 - tw / 2, py + TILE_SIZE / 2 - th / 2 - 6), text, fill = font_color, font = font)
            
            return img
    
        class GameView(discord.ui.View):
            
            def __init__(self, game: Game2048, bot: commands.Bot):
                
                super().__init__(timeout = 300)
                self.game = game
                self.bot = bot

            async def update(self, interaction: discord.Interaction):
                
                buffer = io.BytesIO()
                img = draw_board(self.game.board)
                img.save(buffer, format = "PNG")
                buffer.seek(0)
                
                file = discord.File(buffer, filename = "two-o-four-eight-board.png")

                e = discord.Embed(title = "2048 Game", color = DEFAULT_COLOR, timestamp = datetime.now())
                e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore
                
                if not self.game.is_game_over(): e.add_field(name = "How to Play", value = "Use the arrow buttons below - ⬅️ ⬆️ ➡️ ⬇️ - to move tiles.", inline = False)
                
                if self.game.is_game_over(): e.description = f"### Game Over!\n> - **Score**: **`{self.game.score}`**"
                else: e.description = f"> - **Player**: {member.mention}\n> - **Score**: **`{self.game.score}`**\n> - **Started At**: <t:{start}:R>"
                
                e.set_image(url = "attachment://two-o-four-eight-board.png")
                
                if interaction.response.is_done(): await interaction.edit_original_response(embed = e, view = self, attachments = [file])
                else: await interaction.response.edit_message(embed = e, view = self, attachments = [file])
                    
            @discord.ui.button(label = "⬅️", style = discord.ButtonStyle.secondary)
            async def left(self, interaction: discord.Interaction, button: discord.ui.Button):
                
                if not interaction.user.id == member.id: 
                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"This isn't your 2048 game.", bot = self.bot), ephemeral = True) # type: ignore
                    return
                
                old_board = self.game.board.copy()
                self.game.move_left()
                if self.game.board != old_board: self.game.place_random()
                await self.update(interaction)

            @discord.ui.button(label = "⬆️", style = discord.ButtonStyle.secondary)
            async def up(self, interaction: discord.Interaction, button: discord.ui.Button):
                
                if not interaction.user.id == member.id: 
                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"This isn't your 2048 game.", bot = self.bot), ephemeral = True) # type: ignore
                    return
                
                old_board = self.game.board.copy()
                self.game.move_up()
                if self.game.board != old_board: self.game.place_random()
                await self.update(interaction)

            @discord.ui.button(label = "➡️", style = discord.ButtonStyle.secondary)
            async def right(self, interaction: discord.Interaction, button: discord.ui.Button):
                
                if not interaction.user.id == member.id: 
                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"This isn't your 2048 game.", bot = self.bot), ephemeral = True) # type: ignore
                    return
                
                old_board = self.game.board.copy()
                self.game.move_right()
                if self.game.board != old_board: self.game.place_random()
                await self.update(interaction)

            @discord.ui.button(label = "⬇️", style = discord.ButtonStyle.secondary)
            async def down(self, interaction: discord.Interaction, button: discord.ui.Button):
                
                if not interaction.user.id == member.id: 
                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"This isn't your 2048 game.", bot = self.bot), ephemeral = True) # type: ignore
                    return
                
                old_board = self.game.board.copy()
                self.game.move_down()
                if self.game.board != old_board: self.game.place_random()
                await self.update(interaction)
            
            async def on_timeout(self):
                
                if not self.game.is_game_over():
                    
                    buffer = io.BytesIO()
                    img = draw_board(self.game.board)
                    img.save(buffer, format = "PNG")
                    buffer.seek(0)
                    
                    file = discord.File(buffer, filename = "two-o-four-eight-board.png")

                    e = discord.Embed(title = "2048 Game", color = DEFAULT_COLOR, timestamp = datetime.now())
                    e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore
                
                    e.description = f"### Game Over! (Timed Out)\n> - **Score**: **`{self.game.score}`**"
                    e.set_image(url = "attachment://two-o-four-eight-board.png")
                    
                    if interaction.response.is_done(): await interaction.edit_original_response(embed = e, view = self, attachments = [file])
                    else: await interaction.response.edit_message(embed = e, view = self, attachments = [file])
                        
        game = Game2048()
        view = GameView(game, self.bot)
        
        buffer = io.BytesIO()
        img = draw_board(game.board)
        img.save(buffer, format = "PNG")
        buffer.seek(0)

        file = discord.File(buffer, filename = "two-o-four-eight-board.png")
        
        e = discord.Embed(title = "2048 Game", color = DEFAULT_COLOR, timestamp = datetime.now())
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore
        
        e.description = f"> - **Player**: {member.mention}\n> - **Score**: **`{game.score}`**\n> - **Started At**: <t:{start}:R>"
        e.set_image(url = "attachment://two-o-four-eight-board.png")
        
        e.add_field(name = "How to Play", value = "Use the arrow buttons below - ⬅️ ⬆️ ➡️ ⬇️ - to move tiles.", inline = False)

        await interaction.response.send_message(embed = e, view = view, file = file)        
    
    # /quote
    @app_commands.command(name = "quote", description = "Search or add to the quote bank.")
    @app_commands.describe(member = "The member to get a random quote from, optional", add = "The link of the message to add, optional")
    async def quote(self, interaction: discord.Interaction, member: discord.Member | None = None, add: str = ""):
        
        LINK_REGEX = re.compile(r"https://discord\.com/channels/(\d+)/(\d+)/(\d+)")
        
        if not isinstance(interaction.channel, discord.TextChannel):
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"This command should be used in the text channel with the quote.", bot = self.bot), ephemeral = True) 
            return
        
        def parse_message_link(link: str):
            
            match = LINK_REGEX.match(link)
            
            if not match: raise ValueError("Could not parse that message link.")
            
            guild_id = int(match.group(1))
            channel_id = int(match.group(2))
            message_id = int(match.group(3))
            
            if guild_id != int(GUILD_ID): raise ValueError("That message is not from this server.") # type: ignore

            return (channel_id, message_id)

        if add != "":
            
            guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
            
            try: 
                
                channel_id, message_id = parse_message_link(add)
                
                channel = guild.get_channel(channel_id) # type: ignore
                if channel is None: channel = await guild.fetch_channel(channel_id) # type: ignore
                msg = await channel.fetch_message(message_id) # type: ignore
            
            except Exception as e: 
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
                return
            
            m: discord.Member = interaction.user # type: ignore
            
            elitist_role = guild.get_role(ELITIST_ROLE) # type: ignore
            server_booster_role = guild.get_role(SERVER_BOOSTER_ROLE) # type: ignore
            
            shades_plus_plus_role = guild.get_role(SHADES_PLUS_PLUS_ROLE) # type: ignore
            staff_role = guild.get_role(STAFF_ROLE) # type: ignore
            
            privileged = (elitist_role in m.roles) or (server_booster_role in m.roles) or (is_at_least_level(m, SHADES_PLUS_PLUS_ROLE)) or (is_staff(m))

            if not privileged:
                
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Adding quotes to the quote bank requires being at least {shades_plus_plus_role.mention}, or having one of {elitist_role.mention} or {server_booster_role.mention} or {staff_role.mention}.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
                return
            
            if not msg.content:
                
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not find the message for the link provided in `{add}`, make sure you are in the channel the quote was made in.", bot = self.bot), ephemeral = True) # type: ignore
                return
            
            if len(msg.content) > 100:
                
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"The quote message is too long (max of `{100}` characters).", bot = self.bot), ephemeral = True) # type: ignore
                return
            
            q = {"author-id": msg.author.id, "author-name": str(msg.author), "content": escape_mentions(msg.content), "timestamp": int(msg.created_at.timestamp()), # type: ignore
                 "message-id": msg.id, "channel-id": msg.channel.id} 
            
            all_quotes = await quotes.get_all_quotes()
            for (a_quote_id, a_user_id, a_message_id, a_content, a_timestamp) in all_quotes:
                
                if a_message_id == q["message-id"]: # check for duplicates
                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"This quote is already in the database.", bot = self.bot), ephemeral = True) # type: ignore
                    return
                
            quote_id = await quotes.add_quote(q["author-id"], q["message-id"], q["content"], q["timestamp"])
            await interaction.response.send_message(embed = basic_embed(title = "Member Quote", description = f"Quote has been added to the database with ID `{quote_id}`.", bot = self.bot)) 
            
        elif add == "":
            
            await interaction.response.defer()
            
            guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
            
            pool: list = list(await quotes.get_all_quotes()) or []
            if member: pool = [p for p in pool if p[1] == member.id]
            
            if len(pool) == 0:
                await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Could not find any quotes {f" (for member {member.mention})" if member else ""}", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(users = True)) # type: ignore
                return
                
            (quote_id, user_id, message_id, content, timestamp) = random.choice(pool)
            
            quote_author = guild.get_member(user_id) # type: ignore

            # Get avatar
            async with aiohttp.ClientSession() as session:
                async with session.get(quote_author.display_avatar.url) as resp: # type: ignore
                    avatar_bytes = await resp.read()
                    
            avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            avatar = avatar.resize((128, 128))
            
            # Generate quote image
            img = Image.new("RGBA", (900, 300), (54, 57, 63))
            draw = ImageDraw.Draw(img)
            
            try: font = ImageFont.truetype("fonts/arial.ttf", 36)
            except: font = ImageFont.load_default(size = 36)
            
            try: small_font = ImageFont.truetype("fonts/arial.ttf", 18)
            except: small_font = ImageFont.load_default(size = 18)
            
            wrapped = textwrap.fill(content, width = 30)
            draw.text((200, 80), f'{wrapped}', font = font, fill = "white")
            
            date = datetime.fromtimestamp(int(timestamp))
            footer = f"— {quote_author.name}, {date.strftime("%b %d %Y")} | Quote ID: {quote_id}" # type: ignore
            draw.text((200, 200), footer, font = small_font, fill = (200, 200, 200))
            
            img.paste(avatar, (40, 80), avatar)
            
            buffer = io.BytesIO()
            img.save(buffer, "PNG")
            buffer.seek(0)
            
            file = discord.File(buffer, filename = "member_quote.png")
    
            e = discord.Embed(title = f"Member Quote", color = DEFAULT_COLOR, timestamp = datetime.now())
            e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore
            
            e.set_image(url = await upload_asset(self.bot, file))
            await interaction.followup.send(embed = e)
        
    # /tierlist
    @app_commands.command(name = "tierlist", description = "Generate a tierlist in the format of Tiermaker.")
    @app_commands.describe(live = "Toggles live mode and static mode, live mode is recommended for basic use. Overrides items, optional", tiers = "A comma seperared list of the list tiers and their color, like [[S, #1f1f1f], [A, #1fa80d]], or if using default colors just the tiers, like [[S], [A]]", items = "A comma-seperated list of message IDs like [[ID-A, ID-B], [ID-C, ID-D]], where each sublist is a tier", default_names = "Whether to use default tier names S-Z overriding tiers argument, optional", default_colors = "Whether to use default tier colors from tiermaker overriding tiers argument, optional")
    async def tierlist(self, interaction: discord.Interaction, live: bool = True, items: str = "", tiers: str = "", default_names: bool = True, default_colors: bool = True):
        
        if (not live) and (items == ""):
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"If `live` mode is diabled, `items` must be provided.", bot = self.bot), ephemeral = True) # type: ignore
            return
        
        if (tiers == "") and (default_names == default_colors == False):
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"At least one of `tiers`, `default_names` and `default_colors` must be provided.", bot = self.bot), ephemeral = True) # type: ignore
            return
        
        constants = {"tile-size": 128, "label-width": 180, "max-per-row": 10, "max-tiers": 0,
                    "max-images-per-tier": 30, "bg-color": (26, 26, 23)}
        
        def parse_tiers(text: str, default_names: bool, default_colors: bool, length_defaults: int):
            
            text = text[1:]
            text = text[:len(text) - 1]
            
            tiermaker_default_colors = ["ff7f7f", "ffbf7f", "ffdf7f", "ffff7f", "bfff7f", "7fff7f", "7fffff", "7fbfff"]
            tiermaker_default_names = ["S", "A", "B", "C", "D", "E", "F", "Z"]
            
            tiermaker_default_colors = tiermaker_default_colors[:length_defaults]
            tiermaker_default_names = tiermaker_default_names[:length_defaults]
            
            tier_pattern = re.compile(r"\[([^\],]+)(?:,\s*(#[0-9A-Fa-f]{6}))?\]")
            matches = tier_pattern.findall(text)
            
            try:
                
                if text != "" and default_colors == default_names == False:
                    
                    if not matches: raise ValueError("Invalid `tiers` format.")
                    if len(matches) > constants["max-tiers"]: raise ValueError(f"Maximum of `{constants["max-tiers"]}` allowed for `tiers` under your permissions.")
                
            except ValueError as e:
                
                raise e
                
            tiers = []
            
            if not (default_names and default_colors): iterate_length = min(len(matches), length_defaults)
            else: iterate_length = length_defaults
            
            for i in range(iterate_length):
                
                try: 
                    
                    if default_names: _name = tiermaker_default_names[i] 
                    else: _name = matches[i][0].strip()
            
                except: _name = tiermaker_default_names[i] 
                
                try:
                    
                    if default_colors: _color = tiermaker_default_colors[i]
                    else: _color = matches[i][1].replace("#", "").upper()
                
                except: _color = tiermaker_default_colors[i]
                
                tiers.append({"name": _name, "color": _color, "images": []})
        
            return tiers
        
        def parse_items(text: str, max_tiers: int = 8):
            
            text = text.replace("\n", "")
            text = text.replace(" ", "")
            
            if len(text) > 2000:
                raise ValueError("`items` input is too long.")
            
            try: data = ast.literal_eval(text)
            
            except Exception: raise ValueError("Invalid `items` format.")

            if not isinstance(data, list): raise ValueError("`items` must be a list of lists.")
            
            if len(data) > max_tiers: raise ValueError(f"Maximum `{max_tiers}` tiers allowed under your permissions.")       
            
            tiers = []
            
            for tier in data:
                
                if not isinstance(tier, list): raise ValueError("Each tier sublist in `items` must be a list of message IDs.")
                
                ids = []
                
                for msg_id in tier:
                    
                    if not isinstance(msg_id, int): raise ValueError(f"`{msg_id}` is not a valid message ID.")
                    ids.append(msg_id)
            
                tiers.append(ids)
                
            return tiers    
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        
        # Work out max tiers
        
        SUIT_ROLE = 1140049620857266257
        SHADES_PLUS_PLUS_ROLE = 1140049851850162226
        MAX_CLASS_ROLE = 1140049990677450802
        
        suit_mention = guild.get_role(SUIT_ROLE).mention # type: ignore
        shades_plus_plus_mention = guild.get_role(SHADES_PLUS_PLUS_ROLE).mention # type: ignore
        max_class_mention = guild.get_role(MAX_CLASS_ROLE).mention # type: ignore
        
        reached = {SUIT_ROLE: (is_at_least_level(interaction.user, SUIT_ROLE), 4), # type: ignore
                   SHADES_PLUS_PLUS_ROLE: (is_at_least_level(interaction.user, SHADES_PLUS_PLUS_ROLE), 6), # type: ignore
                   MAX_CLASS_ROLE: (is_at_least_level(interaction.user, MAX_CLASS_ROLE), 8)} # type: ignore
    
        for role_id, (has_reached, max_tiers) in reached.items():
            
            if has_reached and constants["max-tiers"] < max_tiers:
                constants["max-tiers"] = max_tiers
        
        if constants["max-tiers"] == 0:
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"You have submitted too many tiers for your permissions. The maximum amount of tiers is as follows:\n> - {suit_mention}: `4`\n> - {shades_plus_plus_mention}: `6`\n> - {max_class_mention}: `8`", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return

        await interaction.response.defer()
        
        if not live:
            
            try:
            
                _item_groups = parse_items(items, constants["max-tiers"]) 
                _tiers = parse_tiers(tiers, default_names, default_colors, len(_item_groups)) # type: ignore

            except ValueError as e:
                
                await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot)) # type: ignore
                return
                
            if len(_tiers) != len(_item_groups): # type: ignore
                
                await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"You have submitted `{len(_tiers)}` tiers but `{len(_item_groups)}` item image groups.", bot = self.bot)) # type: ignore
                return
            
            # Get images
            for tier_index, message_ids in enumerate(_item_groups):
                
                if len(message_ids) * 10 > constants["max-images-per-tier"]:
                    raise ValueError("Too many images in tier.")
                
                for msg_id in message_ids:
                    
                    try: msg = await interaction.channel.fetch_message(msg_id) # type: ignore
                    
                    except: 
                        
                        await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = "Couldn't find messages with images, make sure they are in the same channel.", bot = self.bot)) # type: ignore
                        return
                        
                    for attachment in msg.attachments:
                        
                        data = await attachment.read()
                        
                        img = Image.open(io.BytesIO(data))
                        img = self.normalize_image(img, constants)
                        
                        _tiers[tier_index]["images"].append(img) # type: ignore
                
            canvas = self.render_tierlist(_tiers, constants)
            
            buffer = io.BytesIO()
            canvas.save(buffer, "PNG")
            buffer.seek(0)

            file = discord.File(buffer, filename = "curve_graph.png")
        
            e = discord.Embed(title = f"Tierlist Generator", color = DEFAULT_COLOR, timestamp = datetime.now())
            e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore
            
            e.set_image(url = await upload_asset(self.bot, file))
            await interaction.followup.send(embed = e)

        else:
            
            if not isinstance(interaction.channel, discord.TextChannel):
                await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"You must send this command from a text channel if `live` mode is enabled.", bot = self.bot), ephemeral = True) # type: ignore
                return
            
            if interaction.user.id in self.live_tierlists.keys():
                await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f'You already have a live tierlist active. End it by sending the message "{self.bot.user.mention}/end/tierlist".', bot = self.bot), ephemeral = True) # type: ignore
                return
            
            _tiers = parse_tiers(tiers, default_names, default_colors, constants["max-tiers"]) # type: ignore
            _item_groups = [[] for _ in range(len(_tiers))]
            
            # Send starting list
            canvas = self.render_tierlist(_tiers, constants)
            
            buffer = io.BytesIO()
            canvas.save(buffer, "PNG")
            buffer.seek(0)
            
            file = discord.File(buffer, filename = "tierlist.png")
            
            expiry_timestamp = int(time.time() + 10800)
            
            e = discord.Embed(title = f"Tierlist Generator", description = f'Generating using **live** mode.\n> - **How to Modify**: To add to the tierlist, user {interaction.user.mention} should ping the bot and add the tier in the message, like "{self.bot.user.mention}/add/Tier S". They should also attach the image to upload.\n> - **Time until Locked**: <t:{expiry_timestamp}:F> (<t:{expiry_timestamp}:R>)', color = DEFAULT_COLOR, timestamp = datetime.now()) # type: ignore
            e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore
            
            e.set_image(url = await upload_asset(self.bot, file))
            await interaction.followup.send(embed = e)
            
            reminder_id = await reminders.add_reminder(user_id = BOT_ID, timestamp = expiry_timestamp, channel_id = interaction.channel_id, message = f"tierlistexpire:{interaction.user.id}:{interaction.channel.id}", repeat = False) # type: ignore
            self.wakeup.set() 
                                    
            self.live_tierlists[interaction.user.id] = {"channel": interaction.channel.id, "tiers": _tiers, "constants": constants, "expiry": expiry_timestamp, "reminder": reminder_id}
        
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        
        channel: discord.TextChannel = message.channel # type: ignore
    
        session = self.live_tierlists.get(message.author.id)
        if not session: return
        
        async def resend_tierlist():
              
            canvas = self.render_tierlist(session["tiers"], session["constants"])
                  
            buffer = io.BytesIO()
            canvas.save(buffer, "PNG")
            buffer.seek(0)
            
            expiry_timestamp = session["expiry"]
            file = discord.File(buffer, filename = "tierlist.png")

            description = f'Generating using **live** mode.\n> - **How to Modify**: To add to the tierlist, user {message.author.mention} should ping the bot and add the tier in the message, like "{self.bot.user.mention}/add/Tier S". They should also attach the image to upload.\n> - **Time until Locked**: <t:{expiry_timestamp}:F> (<t:{expiry_timestamp}:R>)' # type: ignore

            e = discord.Embed(title = f"Tierlist Generator", description = description, color = DEFAULT_COLOR, timestamp = datetime.now()) # type: ignore
            e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore
            
            e.set_image(url = await upload_asset(self.bot, file))
            await channel.send(embed = e)

        
        mention1 = f"<@{self.bot.user.id}>" # type: ignore
        mention2 = f"<@!{self.bot.user.id}>" # type: ignore
        
        if not message.content.startswith((mention1, mention2)): return
        
        action = message.content.split("/", 5)[1]
          
        match action:
            
            case "add":
                
                try:
     
                    tier_name = message.content.split("/", 5)[2]
                    tier_index = -1
                    
                    for i, tier in enumerate(session["tiers"]):
                              
                        if tier["name"] == tier_name:
                            
                            tier_index = i
                            break
                    
                    if tier_index < 0: return
                    
                    if not message.attachments: 
                        await channel.send(embed = basic_embed(title = "Error Encountered!", description = f"You must attach at least one image to be added.", bot = self.bot)) 
                        return
                    
                    for attachment in message.attachments:
                        
                        data = await attachment.read()

                        img = Image.open(io.BytesIO(data))
                        img = self.normalize_image(img, session["constants"])
                        
                        session["tiers"][tier_index]["images"].append(img)

                except Exception as e:
                    
                    await channel.send(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot)) 
                    return
                
                await resend_tierlist()
            
            case "delete":
                
                tier_name = message.content.split("/", 5)[2]
                tier_index = -1
                
                for i, tier in enumerate(session["tiers"]):
                    if tier["name"] == tier_name:
                        tier_index = i
                        break
                
                if tier_index < 0: return
                
                try:
                    
                    pos = int(message.content.split("/", 5)[3])
                    
                    images = session["tiers"][tier_index]["images"]
                    
                    if not (1 <= pos < len(images) + 1):
                        
                        await channel.send(embed = basic_embed(title = "Error Encountered!", description = f"Position to delete item must be between `{1}` and `{len(images) + 1}`.", bot = self.bot))
                        return
                    
                    images.pop(pos - 1)

                except Exception as e:
                    
                    await channel.send(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot)) 
                    return
                
                await resend_tierlist()

            case "move":
                
                tier_name = message.content.split("/", 5)[2]
                tier_index = -1
                
                for i, tier in enumerate(session["tiers"]):
                    if tier["name"] == tier_name:
                        tier_index = i
                        break
                
                if tier_index < 0: return
                
                try:
                    
                    original_pos = int(message.content.split("/", 5)[3])
                    final_pos = int(message.content.split("/", 5)[4])
                    
                    images = session["tiers"][tier_index]["images"]
                    
                    original_valid = (1 <= original_pos < len(images) + 1)
                    final_valid = (1 <= final_pos < len(images) + 1)
                        
                    if not (original_valid and final_valid):
                        
                        await channel.send(embed = basic_embed(title = "Error Encountered!", description = f"Positions to move items must be between `{1}` and `{len(images) + 1}`.", bot = self.bot))
                        return
                    
                    item = images.pop(original_pos - 1)
                    images.insert(final_pos - 1, item)
                    
                except Exception as e:
                    
                    await channel.send(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot)) 
                    return

                await resend_tierlist()
                
            case "end":
                
                if message.content.split("/", 5)[2] == "tierlist":
                    
                    reminder_id: int = session["reminder"]
                    await reminders.delete_reminder(reminder_id)

                    del self.live_tierlists[message.author.id]
             
                    await channel.send(embed = basic_embed(title = "Tierlist Generator", description = f"Live tierlist ended for member {message.author.mention}.", bot = self.bot))
                    return
            
            case _:
                
                return
                    
    # /event
    @app_commands.command(name = "event", description = "Create a community server event.")
    async def event(self, interaction: discord.Interaction):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        member = interaction.user # type: ignore
        
        server_booster_role = guild.get_role(SERVER_BOOSTER_ROLE) # type: ignore
        
        classy_role = guild.get_role(CLASSY_ROLE) # type: ignore

        privileged = (server_booster_role in member.roles) or (is_at_least_level(member, CLASSY_ROLE)) # type: ignore

        if not privileged:
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Creating an event requires being at least {classy_role.mention}, or having one of {server_booster_role.mention}.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return  
        
        cooldown = {CLASSY_ROLE: 2628000, CLASSY_PLUS_ROLE: 1209600, MAX_CLASS_ROLE: 604800, SERVER_BOOSTER_ROLE: 604800}
        our_cooldown = 2628000
        
        for role in [guild.get_role(r) for r in [CLASSY_ROLE, CLASSY_PLUS_ROLE, MAX_CLASS_ROLE, SERVER_BOOSTER_ROLE]]: # type: ignore
            if role in member.roles or is_at_least_level(member, role): # type: ignore
                our_cooldown = cooldown[role.id] # type: ignore
                
        all_reminders = await reminders.get_due_reminders()        
        for (reminder_id, user_id, timestamp, repeat, channel_id, message) in all_reminders:
            
            if int(user_id) == int(BOT_ID) and message == f"cooldown:event:{member.id}":
                
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"You have a cooldown to using this command until <t:{timestamp}:F> (<t:{timestamp}:R>).", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore)
                return
            
        class EventModal(discord.ui.Modal):
            
            def __init__(self, bot, wakeup: asyncio.Event):
                
                super().__init__(title = "Event Form")
                
                self.add_item(discord.ui.TextInput(label = "Name", placeholder = "What do we call your event..."))
                self.add_item(discord.ui.TextInput(label = "Description", placeholder = "A description of your event... (optional)", style = discord.TextStyle.paragraph, required = False))
                self.add_item(discord.ui.TextInput(label = "Date", placeholder = "The day it is on in format (YYYY-MM-DD), e.g. 2026-24-07"))
                self.add_item(discord.ui.TextInput(label = "Time", placeholder = "The UTC time range in format (HH:MM)-(HH:MM), e.g. 06:30-18:45"))
                self.add_item(discord.ui.TextInput(label = "Location", placeholder = "Where the event is going to be, can be showcase thread ID... (optional)", style = discord.TextStyle.paragraph, required = False))
                
                self.bot = bot
                self.wakeup = wakeup
            
            def next_date_time(self, _date, _time):
                
                try:
                    
                    today = datetime.today()
                    target = datetime(year = _date.year, 
                                      month = _date.month, 
                                      day = _date.day, 
                                      hour = _time.hour, 
                                      minute = _time.minute)
                
                except:
                    
                    raise ValueError("Invalid date/time combination.")

                
                return target
            
            async def on_submit(self, interaction: discord.Interaction):
                
                name = self.children[0].value # type: ignore
                description = self.children[1].value # type: ignore
                date = self.children[2].value # type: ignore
                _time = self.children[3].value # type: ignore
                location = self.children[4].value # type: ignore
            
                thread = None
                
                try:
                    
                    try: date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo = ZoneInfo("UTC"))
                    except ValueError: raise AssertionError(f"`date` is not a valid date.")
                    
                    try: 
                        start_clock = datetime.strptime(_time.split('-')[0], "%H:%M").time()
                        end_clock   = datetime.strptime(_time.split('-')[1], "%H:%M").time()

                        start_time = datetime.combine(date.date(), start_clock, tzinfo=ZoneInfo("UTC"))
                        end_time = datetime.combine(date.date(), end_clock, tzinfo=ZoneInfo("UTC"))
                        
                        if end_time <= start_time: end_time += timedelta(days = 1)
                        
                    except ValueError: raise AssertionError(f"`time` is not a valid time range.")
                    
                    assert end_time > start_time, f"`end_time` must be after `start_time`."
                    assert datetime.now(tz = ZoneInfo("UTC")) < start_time, f"`start_time` must be in the future."
                    
                    if location:
                        
                        try: 
                            
                            thread_id = int(location)
                            thread = guild.get_channel_or_thread(thread_id) # type: ignore
                            
                        except: pass
                
                except AssertionError as e:
                    
                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
                    return
                
                target_start_date = int(self.next_date_time(date, start_time).timestamp())
                target_end_date = int(self.next_date_time(date, end_time).timestamp())
                
                event = await guild.create_scheduled_event(name = name, description = description, start_time = start_time, end_time = end_time, location = thread.name if thread else None, entity_type = discord.EntityType.external, privacy_level = discord.PrivacyLevel.guild_only) # type: ignore
                await reminders.add_reminder(BOT_ID, target_start_date - 300, interaction.channel_id, message = f"event:{member.id}:{target_start_date}:{target_end_date}:{thread.id if thread else None}", repeat = None) # type: ignore
                await reminders.add_reminder(BOT_ID, int(datetime.now().timestamp()) + our_cooldown, interaction.channel_id, message = f"cooldown:event:{member.id}", repeat = None) # type: ignore
                
                self.wakeup.set()
                        
                await interaction.response.send_message(embed = basic_embed(title = "Event Form", description = f"Event created.", bot = self.bot), ephemeral = True)
        
        await interaction.response.send_modal(EventModal(bot = self.bot, wakeup = self.wakeup)) 
        
    # /play
    @app_commands.command(name = "play", description = "Stream a music song in VC.")
    @app_commands.describe(query = "The song to look for. Can be a Spotify link.")
    async def play(self, interaction: discord.Interaction, query: str):
        
        await interaction.response.defer()
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        m = interaction.user # type: ignore
        
        shades_plus_role = guild.get_role(SHADES_PLUS_ROLE) # type: ignore
        staff_role = guild.get_role(STAFF_ROLE) # type: ignore
        
        permissions = is_at_least_level(m, SHADES_PLUS_ROLE) or is_staff(m) # type: ignore
        
        if not permissions:
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Starting a music session requires being at least {shades_plus_role.mention} or being {staff_role.mention}.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return

        if not interaction.user.voice: # type: ignore
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"You must send this command from a voice channel.", bot = self.bot), ephemeral = True) # type: ignore
            return
        
        channel: discord.VoiceChannel = interaction.user.voice.channel # type: ignore
        
        if is_spotify(query): query = spotify_to_query(self.sp, query)
        vc = guild.voice_client # type: ignore
        
        if not vc:
            
            if not interaction.user.voice: # type: ignore
                await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Join a voice channel.", bot = self.bot), ephemeral = True) 
                return
                
            vc = await interaction.user.voice.channel.connect() # type: ignore
        
        player = get_player(self.bot, guild) # type: ignore
        
        try:
            song = await extract_song(query)
            
        except Exception as e:
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Couldn't play this track: {e}", bot = self.bot), ephemeral = True) 
            return
        
        if len(player.queue._queue) >= 30:
            await interaction.followup.send(embed = basic_embed(title = "Error Encountered!", description = f"Queue is too long (max of `{30}` songs).", bot = self.bot), ephemeral = True) 
            return
            
        if not player.controller:
             
            controller_msg = await interaction.followup.send(embed = basic_embed(title = "🎵 Music Controller", description = f"Starting playback...", bot = self.bot))
            
            player.controller = controller_msg
            await player.update_controller()
            
            for r in CONTROLS: await controller_msg.add_reaction(r) # type: ignore
        
        else:
            
            await interaction.followup.send(embed = basic_embed(title="🎵 Queued", description=f"Added **{song.title}** to the queue.", bot = self.bot))
        
        await player.queue.put(song)
    
    # /controller
    @app_commands.command(name = "controller", description = "Get the music controller.")
    async def controller(self, interaction: discord.Interaction):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        player = get_player(self.bot, guild) # type: ignore
        
        if not player:
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Nothing is playing.", bot = self.bot), ephemeral = True) # type: ignore
            return
        
        if not player.controller:
            
            try: await player.controller.delete()
            except: pass
            
        msg = await interaction.response.send_message(embed = basic_embed(title = "🎵 Music Controller", description = "Controller moved.", bot = self.bot))
        msg = await interaction.original_response()
        
        player.controller = msg
        
        for r in CONTROLS: await msg.add_reaction(r)
        await player.update_controller()
        
    # /remove
    @app_commands.command(name = "remove", description = "Remove a song from the queue.")
    @app_commands.describe(index = "Position of the song in the queue.")
    async def remove(self, interaction: discord.Interaction, index: int):
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        m = interaction.user # type: ignore

        player = get_player(self.bot, guild) # type: ignore
        
        if not player:
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Nothing is playing.", bot = self.bot), ephemeral = True) # type: ignore
            return
        
        shades_plus_role = guild.get_role(SHADES_PLUS_ROLE) # type: ignore
        staff_role = guild.get_role(STAFF_ROLE) # type: ignore
        
        permissions = is_at_least_level(m, SHADES_PLUS_ROLE) or is_staff(m) # type: ignore
        
        if not permissions:
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Removing a song from the queue requires being at least {shades_plus_role.mention} or being {staff_role.mention}.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return

        queue = list(player.queue._queue)

        if index < 1 or index > len(queue):
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Invalid song position: must be between `{1}` and `{len(queue)}`.", bot = self.bot), ephemeral = True) 
            return
    
        removed = queue.pop(index - 1)
        
        player.queue._queue.clear()
        for s in queue: player.queue._queue.append(s)
        
        await interaction.response.send_message(embed = basic_embed(title = "🎵 Removed", description = f"**{removed.title}** has been removed from the queue.", bot = self.bot)) 
        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):  
        
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
        member = guild.get_member(payload.user_id)  # type: ignore
        
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id) # type: ignore
        
        if member.bot: return # type: ignore
        player = players.get(guild.id) # type: ignore
        
        if not player: return
        if payload.message_id != player.controller.id: return # type: ignore
        
        vc: discord.VoiceClient = guild.voice_client # type: ignore
        
        match str(payload.emoji):
        
            case "⏯":
                
                if vc.is_playing(): vc.pause()
                else: vc.resume()
            
            case "⏭":
                
                vc.stop()
                
            case "⏹":
                
                await vc.disconnect()
                players.pop(guild.id, None) # type: ignore
                
            case "🔁":
                
                player.loop = not player.loop
            
            case "📜":
                
                items = list(player.queue._queue)
                
                if not items: await channel.send(embed = basic_embed(title = "🎵 Music Controller", description = f"Queue empty.", bot = self.bot)) # type: ignore
                else: await channel.send(embed = basic_embed(title = "🎵 Music Controller", description = "\n".join(f"{i+1}. {s.title}" for i, s in enumerate(items)), bot = self.bot)) # type: ignore
                
        await message.remove_reaction(payload.emoji, member) # type: ignore

        
        