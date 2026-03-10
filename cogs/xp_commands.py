# cogs > xp_commands.py // @toblobs // 10.03.26

from datetime import timedelta
import time
from .__init__ import *

import re
import io
import asyncio
import math

from typing import List, Tuple

from discord import TextChannel, app_commands
from discord.ext import commands

import numpy as np
from PIL import Image
import emoji

import matplotlib.pyplot as plt 
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator, StrMethodFormatter
from matplotlib.lines import Line2D

from cogs import get_top_colored_role, upload_asset
from cogs.utils.embeds import basic_embed
from cogs.utils.permissions import *

from database import XP_COOLDOWN, XP_ENABLED, XP_MIN, XP_MAX, dbio, leaderboard, rank, reward_roles, schema, sync, users, xp

class XPCommands(commands.Cog):

    def __init__(self, bot: commands.Bot):

        self.bot = bot
    
    ### generally used submodules
    def get_frozen_xp(self, member_id: int) -> int:

        with open(r"C:\Users\Tobil\Documents\botlobs\database\frozen-xp.txt") as f:

            for line in f:

                if '-' not in line:
                    continue

                user_id, xp = line.split("-")
                user_id = int(user_id.strip())
                xp = int(xp.strip())
                
                if user_id == member_id:
                    return xp
        
        return 0

    def generate_progress_gradient(self, percentage: int, hexes: list[str]) -> io.BytesIO:

        gen_cog = self.bot.get_cog("GeneralCommands")
        WIDTH, HEIGHT = (512, 32)

        percentage = max(0, min(percentage, 100)) # clamp 0 to 100

        filled_width = int(WIDTH * percentage / 100)
        empty_width = WIDTH - filled_width

        final_image = Image.new("RGB", (WIDTH, HEIGHT), (26, 26, 30))

        if filled_width > 0:
            gradient_buffer = gen_cog.generate_color_image((filled_width, HEIGHT), hexes) # type: ignore
            gradient_image = Image.open(gradient_buffer)
            final_image.paste(gradient_image, (0, 0))

        
        buffer = io.BytesIO()
        final_image.save(buffer, "PNG")
        buffer.seek(0)

        return buffer
    
    async def level_up_message(self, member, level, current_xp, xp_gained, full_xp_to_next, xp_to_next, obtained_roles):
        
        BOT_CHANNEL = 1138183014178902097
        bot_channel = self.bot.get_channel(BOT_CHANNEL) # type: ignore

        e = discord.Embed(title = "🚀 Level Up", color = DEFAULT_COLOR, timestamp = datetime.now(), description = f"{member.mention} has levelled up to level **{level}**!")
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

        e.add_field(name = "✨ Current XP", value = f"`{current_xp:,}`", inline = False)
        e.add_field(name = "⏩ XP to Next Level", value = f"`{xp_gained:,}`/`{full_xp_to_next:,}` (`{xp_to_next:,}` more)", inline = False)

        if obtained_roles: e.add_field(name = "🎁 Obtained Roles", value = "You have been rewarded with the role(s): " + ", ".join([r.mention for r in obtained_roles])) # type: ignore

        await bot_channel.send(embed = e) # type: ignore
        
    ### commands

    # /leaderboard
    @app_commands.command(name = "leaderboard", description = "Shows the server XP leaderboard.")
    @app_commands.describe(page = "The page to jump to", member = "The member to jump to, overrides page", last = "An argument to only check for XP gained in the last day/week/month", graph = "Whether to generate a graph using other arguments, can be slow")
    @app_commands.choices(last = [app_commands.Choice(name = "All Time", value = "all"), app_commands.Choice(name = "Last Day", value = "daily"), app_commands.Choice(name = "Last Week", value = "weekly"), app_commands.Choice(name = "Last Month", value = "monthly")])
    async def leaderboard(self, interaction: discord.Interaction, page: int | None = 1, member: discord.Member | None = None, last: app_commands.Choice[str] = "all", graph: bool | None = False): # type: ignore
        
        time_periods = {"daily": 86400, "weekly": 604800, "monthly": 2592000}

        # Work out last timestamp
        if last != "all": 

            period = last.value

            timestamp = 0

            now = int(time.time())
            timestamp = now - time_periods[period]

        else: 

            period = "all"

            timestamp = 0

        # Defer if graph
        if graph: await interaction.response.defer()

        if graph:

            # Build cumulative data
            if page is None: page = 1

            if member is not None: 

                member_rank = await rank.get_time_filtered_rank(timestamp, member.id)
                if member_rank: page = math.ceil(member_rank / 10) # type: ignore
                else: page = 1
            
            if period != "all":
                members = await leaderboard.time_filtered_leaderboard_page(timestamp, page - 1)
            
            else:
                members = await leaderboard.time_filtered_leaderboard_page(timestamp, page = 0)
            
            member_ids = [int(m[0]) for m in members]

            # Get member colors
            
            member_colors = {}
            guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore

            for member_id in member_ids:
                
                if guild: member = guild.get_member(member_id)
 
                if member: 
                    top_colored_role = get_top_colored_role(member)
                    
                    if top_colored_role: member_colors[member_id] = f"#{top_colored_role.color.value:06x}"
                    else: member_colors[member_id] = "#ffffff"

            logs_query = await leaderboard.get_xp_logs(timestamp, member_ids)
            xp_data = {}

            for m in member_ids: xp_data[m] = []
            cumulative = {m: self.get_frozen_xp(m) if period == "all" else 0 for m in member_ids}
            
            for (member_id, timestamp, xp) in logs_query: 
                cumulative[member_id] += xp
                xp_data[member_id].append((timestamp, cumulative[member_id]))

            # Forward Fill
            all_ts = [t for member_data in xp_data.values() for t, _ in member_data]
            start_dt = datetime.fromtimestamp(min(all_ts))
            end_dt = datetime.fromtimestamp(max(all_ts))
            
            if last != "all": 
                hours = time_periods[period] / 86400 
                
            else: 
                hours = time_periods["daily"] / 86400 # for all, default to monthly

            interval = timedelta(hours = hours)
            timeline = []

            current = start_dt
            while current <= end_dt:
                timeline.append(current)
                current += interval
            
            # Plot
            fig, ax = plt.subplots()

            for member_id, data in xp_data.items():
                
                data = xp_data[member_id]
                if not data: continue

                timestamp_to_xp = {datetime.fromtimestamp(t): xp for t, xp in data}

                y_ff = []
                last_xp = 0

                for t in timeline:
                    
                    previous_times = [ts for ts in timestamp_to_xp if ts <= t]
                    if previous_times: last_xp = timestamp_to_xp[max(previous_times)]
                    y_ff.append(last_xp)

                name = self.bot.get_guild(int(GUILD_ID)).get_member(member_id) # type: ignore
                ax.plot(timeline, y_ff, label = name, color = member_colors.get(member_id, "#ffffff"))

            plt.legend()
            plt.xlabel("Time")
            plt.ylabel("XP")

            fig.patch.set_facecolor("#1a1a1e")
            ax.set_facecolor("#1a1a1e")

            ax.xaxis.label.set_color("white")
            ax.yaxis.label.set_color("white")

            ax.tick_params(axis = "both", colors = "white")

            ax.grid(axis = "y", linestyle = "--", alpha = 0.2, color = "white")

            for spine in ax.spines.values():
                spine.set_color("white")

            locator = mdates.AutoDateLocator()
            formatter = mdates.ConciseDateFormatter(locator)

            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)

            ax.yaxis.set_major_locator(MaxNLocator(integer = True))
            ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))

            legend = ax.legend(framealpha = 0, frameon = False, labelcolor = "white", fontsize = 11)
            fig.autofmt_xdate()

            plt.tight_layout()

            buffer = io.BytesIO()
            plt.savefig(buffer, format = "png")
            buffer.seek(0)

            plt.close()

            file = discord.File(buffer, filename = "leaderboard_graph.png")

            e = discord.Embed(title = f"Server XP Leaderboard Graph", color = DEFAULT_COLOR, timestamp = datetime.now())
            e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

            e.set_image(url = await upload_asset(self.bot, file))
            await interaction.followup.send(embed = e)

        else:

            async def build_leaderboard_embed(guild, title, rows, page, searched_member_id = None,):

                e = discord.Embed(title = title, color = DEFAULT_COLOR, timestamp = datetime.now())
                e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

                start_rank = (page - 1) * 10 + 1
                lines = []

                for i, (member_id, xp, level) in enumerate(rows):

                    rank = start_rank + i

                    member = guild.get_member(member_id)

                    if member is None: name = f"<@{member_id}>"
                    else: name = member.mention

                    if searched_member_id == member_id:

                        line = f"**{rank}) Lv. ({level}) - {name} ({xp:,} XP)**"
                        lines.append(line)

                    else:

                        line = f"**{rank})** Lv. ({level}) - {name} ({xp:,} XP)"
                        lines.append(line)

                e.description = "\n".join(lines)
                e.set_footer(text = f"Page {page}")

                return e
            
            class PageSelect(discord.ui.Select):

                def __init__(self, parent_view: discord.ui.View, count):

                    self.parent_view = parent_view

                    total_users = count
                    total_pages = math.ceil(total_users / 10)

                    options = []

                    for page in range(1, total_pages + 1):

                        options.append(discord.SelectOption(label = f"Page {page}", value = str(page)))
                        super().__init__(placeholder = "Jump to page...", min_values = 1, max_values = 1, options = options)

                async def callback(self, interaction: discord.Interaction):

                    page = int(self.values[0])
                    self.parent_view.page = page # type: ignore

                    e = await self.parent_view.load_page() # type: ignore

                    await interaction.response.edit_message(embed = e, view = self.parent_view)

                async def interaction_check(self, interaction) -> bool:
                    return interaction.user.id == self.parent_view.user_id # type: ignore

            class LeaderboardView(discord.ui.View):

                def __init__(self, interaction, page = 1, timestamp = None, count = 0, member_id = None):

                    super().__init__(timeout = 300)

                    self.page = page
                    self.timestamp = timestamp
                    self.guild = interaction.guild
                    self.user_id = interaction.user.id

                    self.member_id = member_id

                    self.add_item(PageSelect(self, count))

                async def load_page(self):
                    
                    if self.timestamp: rows = await leaderboard.time_filtered_leaderboard_page(self.timestamp, self.page - 1)
                    else: rows = await leaderboard.leaderboard_page(self.page - 1)
                    
                    new_rows = []

                    for r in rows:
                        
                        if self.timestamp:

                            user_id = r[0]
                            xp = r[1]

                            level = await users.get_user_level(user_id)

                            new_rows.append([user_id, xp, level])

                        else:

                            new_rows.append(list(r))
                
                    if not self.timestamp: title = "Server XP Leaderboard"
                    else: title = f"Server XP Leaderboard ({last.name})"

                    return await build_leaderboard_embed(self.guild, title, new_rows, self.page, searched_member_id = self.member_id)
                
                @discord.ui.button(label = "◀ Previous")
                async def previous(self, interaction, button):

                    if self.page > 1:
                        self.page -= 1
                    
                    embed = await self.load_page()
                    await interaction.response.edit_message(embed = embed, view = self)

                @discord.ui.button(label = "Next ▶")
                async def next(self, interaction, button):

                    self.page += 1
                    
                    embed = await self.load_page()
                    await interaction.response.edit_message(embed = embed, view = self)
            
            if page is None: page = 1

            if member is not None: 

                if timestamp > 0: member_rank = await rank.get_time_filtered_rank(timestamp, member.id)
                else: member_rank = await rank.get_rank(member.id)

                if member_rank: page = math.ceil(member_rank / 10) # type: ignore

                member_id = member.id
            
            else:
                member_id = None
                
            total_users = int(await rank.total_users())

            view = LeaderboardView(interaction, page = page, timestamp = timestamp, count = total_users, member_id = member_id) # type: ignore

            e = await view.load_page()

            await interaction.response.send_message(embed = e, view = view, allowed_mentions = discord.AllowedMentions(users = True))

    # /curve
    @app_commands.command(name = "curve", description = "Shows the positions of server members on the XP curve.")
    @app_commands.describe(page = "The page to jump to", member = "The member to jump to, overrides page")
    async def curve(self, interaction: discord.Interaction, page: int | None = 1, member: discord.Member | None = None):
        
        await interaction.response.defer()
        
        if page is None: page = 1
        if member is not None:
                   
            member_rank = await rank.get_rank(member.id)
            if member_rank: page = math.ceil(member_rank / 10) # type: ignore
            else: page = 1
        
        members = await leaderboard.leaderboard_page(page - 1)
        
        member_ids = [int(m[0]) for m in members]
        member_xps = [int(m[1]) for m in members]
        member_levels = [int(m[2]) for m in members]
        
        member_partial_levels = []
        
        for i, member_xp in enumerate(member_xps):
            
            member_level = member_levels[i]

            over_level = member_xp - xp.xp_required(member_level)

            xp_to_next = xp.xp_required(member_level + 1) - xp.xp_required(member_level)
            
            partial_level = member_level + (over_level / xp_to_next)
            
            member_partial_levels.append(partial_level)
            

        # Get member colors
            
        member_colors = {}
        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore

        for member_id in member_ids:
            
            if guild: member = guild.get_member(member_id)

            if member: 
                top_colored_role = get_top_colored_role(member)
                
                if top_colored_role: member_colors[member_id] = f"#{top_colored_role.color.value:06x}"
                else: member_colors[member_id] = "#ffffff"
                    
        levels = np.arange(min(member_levels) - 2, max(member_levels) + 3)
        
        xp_exact = 1.5 * levels ** 3 + 15 * levels ** 2 + 150 * levels
        
        legend_lines = []
 
        fig, ax = plt.subplots()
        
        ax.plot(levels, xp_exact, color = "white", linewidth = 2, zorder = 1)

        for member_id in member_ids:
            
            member_obj = self.bot.get_guild(int(GUILD_ID)).get_member(member_id) # type: ignore
            name = member_obj.name if member_obj else "???"
            
            member_level = member_partial_levels[member_ids.index(member_id)]
            member_xp = member_xps[member_ids.index(member_id)]
            
            ax.scatter(member_level, member_xp, color = member_colors.get(member_id, "#ffffff"), s = 80, edgecolor = "white", zorder = 2, label = name)

            legend_lines.append(Line2D([0], [0], color = member_colors.get(member_id, "#ffffff"), lw = 2, label = name))
            
        plt.legend()
        plt.xlabel("Level")
        plt.ylabel("XP")
        
        fig.patch.set_facecolor("#1a1a1e")
        ax.set_facecolor("#1a1a1e")

        ax.xaxis.label.set_color("white")
        ax.yaxis.label.set_color("white")

        ax.tick_params(axis = "both", colors = "white")
        
        ax.grid(axis = "x", linestyle = "--", alpha = 0.2, color = "white")
        ax.grid(axis = "y", linestyle = "--", alpha = 0.2, color = "white")
        
        legend = ax.legend(handles = legend_lines, framealpha = 0, frameon = False, labelcolor = "white", fontsize = 10, loc = "upper left")
        
        for spine in ax.spines.values():
            spine.set_color("white")
            
        ax.yaxis.set_major_locator(MaxNLocator(integer = True))
        ax.yaxis.set_major_formatter(StrMethodFormatter('{x:,.0f}'))
        
        ax.annotate(r"$y = 1.5x^3 + 15x^2 + 150x$", ha = "center", xy = (0.5, 0), xycoords = "axes fraction", xytext = (0, -70), textcoords = "offset points", va = "bottom", color = "white", fontsize = 12)
        
        plt.tight_layout(pad = 2)
        
        buffer = io.BytesIO()
        plt.savefig(buffer, format = "png")
        buffer.seek(0)

        plt.close()
        
        file = discord.File(buffer, filename = "curve_graph.png")
        
        e = discord.Embed(title = f"Server XP Curve Graph", color = DEFAULT_COLOR, timestamp = datetime.now())
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore
        
        e.set_image(url = await upload_asset(self.bot, file))
        await interaction.followup.send(embed = e)
            
    # /multipliers
    @app_commands.command(name = "multipliers", description = "Shows the XP multipliers for roles and channels.")
    @app_commands.describe(member = "Member to show multipliers for")
    async def multipliers(self, interaction: discord.Interaction, member: discord.Member | None = None):

        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore

        cur = await dbio.db.conn.execute("""
            SELECT role_id, channel_id, multiplier
            FROM multipliers
        """)

        rows = await cur.fetchall()
        
        rows = sorted(rows, key = lambda r: r[2], reverse = True)

        roles_str = ""
        channel_str = ""

        e = discord.Embed(title = f"XP Multipliers", color = DEFAULT_COLOR, timestamp = datetime.now(), description = f"")
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore
        
        if rows:

            for (role_id, channel_id, multiplier) in rows:

                role = guild.get_role(role_id) # type: ignore
                if role: roles_str += f"{role.mention} | (`{multiplier}x`) \n"
                
                channel = guild.get_channel(channel_id) # type: ignore
                if channel: channel_str += f"{channel.mention} | (`{multiplier}x`) \n"
        
        e.add_field(name = "Role Multipliers", value = roles_str)
        e.add_field(name = "Channel Multipluers", value = channel_str)

        if member:

            member_multiplier_role = None

            member_multiplier_role_id, member_multiplier = await xp.get_member_highest_multiplier(member)

            if member_multiplier_role_id: member_multiplier_role = guild.get_role(member_multiplier_role_id) # type: ignore

            if member_multiplier_role:
                e.add_field(name = f"🚀 Member Multiplier", value = f"{member_multiplier_role.mention}| (`{member_multiplier}x`)", inline = True) # type: ignore
            else:
                e.add_field(name = "🚀 Member Multiplier", value = f"No multiplier.", inline = True)

        await interaction.response.send_message(embed = e, allowed_mentions = discord.AllowedMentions(roles = True))
        
    # /sync
    @app_commands.command(name = "sync", description = "Syncs a member's level roles.")
    @app_commands.describe(member = "Member to sync the roles of, defaults to user")
    async def sync(self, interaction: discord.Interaction, member: discord.Member | None = None):

        member = member or interaction.user # type: ignore

        if member != interaction.user and not is_moderator(interaction.user): # type: ignore

            guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Using `member` is a permission for {guild.get_role(MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            return

        elif member:

            current_xp, level, prestige, intro_text, birthday, country = await users.get_user(member.id) # type: ignore
            added_roles = removed_roles = []

            added_roles, removed_roles = await sync.sync_roles(member, level, self.bot)

            e = discord.Embed(title = f"Sync Roles", color = DEFAULT_COLOR, timestamp = datetime.now(), description = f"")
            e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

            if added_roles:

                e.add_field(name = "Added Roles", value = ", ".join([a.mention for a in added_roles]), inline = False) # type: ignore

            if removed_roles:

                e.add_field(name = "Removed Roles", value = ", ".join([a.mention for a in removed_roles]), inline = False) # type: ignore

            if (added_roles == removed_roles == []):

                e.description = "No roles added or removed in sync."
            
            await interaction.response.send_message(embed = e, allowed_mentions = discord.AllowedMentions(roles = True))

        else:

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not fetch role information for this member.", bot = self.bot), ephemeral = True) # type: ignore
            return

    # /rank
    @app_commands.command(name = "rank", description = "Shows a member's rank card.")
    @app_commands.describe(member = "Member to get rank card of, defaults to user")
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None):

        member = member or interaction.user # type: ignore
            
        if not member: 

            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not fetch XP info about this member.", bot = self.bot), ephemeral = True)
            return

        # Get XP information
        current_xp, level, prestige, intro_text, birthday, country = await users.get_user(member.id) # type: ignore

        if (current_xp == None) or (level == None):
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not fetch XP info about this member.", bot = self.bot), ephemeral = True)
            return

        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore

        name = member.name
        mention = member.mention

        cooldown = int(xp.get_member_cooldown(member))
        multiplier_role_id, multiplier = await xp.get_member_highest_multiplier(member)
        multipler_role = guild.get_role(multiplier_role_id) # type: ignore

        full_xp_to_next = xp.xp_required(level = level + 1) - xp.xp_required(level = level)

        xp_gained = current_xp - xp.xp_required(level = level)
        xp_to_next = full_xp_to_next - xp_gained

        percentage = (xp_gained / full_xp_to_next) * 100

        messages_left = [int((full_xp_to_next - xp_gained) / int(XP_MIN * multiplier)), int((full_xp_to_next - xp_gained) / int(XP_MAX * multiplier))]

        # Get top colored role
        top_colored_role = get_top_colored_role(member)

        if top_colored_role: 

            role_hexes = [f"{top_colored_role.color.value:06X}"] # default if no gradient # type: ignore
            if top_colored_role.secondary_color: role_hexes.append(f"#{top_colored_role.secondary_color.value:06X}") # type: ignore
            if top_colored_role.tertiary_color: role_hexes.append(f"#{top_colored_role.tertiary_color.value:06X}") # type: ignore
    
        else:

            role_hexes = [f"{DEFAULT_COLOR.value:06X}"]

        buffer = self.generate_progress_gradient(percentage, role_hexes)
        file = discord.File(buffer, filename = "rank_bar.png")

        # Generate embed
        e = discord.Embed(title = f"Rank Card", color = DEFAULT_COLOR, timestamp = datetime.now(), description = f"{mention} **Rank Card**")
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore
        
        e.add_field(name = "✨ XP", value = f"`{current_xp:,}` (level **{level}**)", inline = True)
        e.add_field(name = "⏩ Next Level", value = f"`{xp_gained:,}`/`{full_xp_to_next:,}` (`{xp_to_next:,}` more)", inline = True)
        e.add_field(name = "🕓 Cooldown", value = f"`00:{(XP_COOLDOWN - cooldown):02}`" if cooldown < XP_COOLDOWN else "`None`", inline = True)
        
        if multipler_role:
            e.add_field(name = "🚀 Multiplier", value = f"{multipler_role.mention} (`{multiplier}x`)", inline = True) # type: ignore
        else:
            e.add_field(name = "🚀 Multiplier", value = f"No multiplier.", inline = True)
    
        e.add_field(name = "📊 Percentage Bar", value = f"`{round(percentage, 2)}%`, `{messages_left[1]:,}` - `{messages_left[0]:,}` messages left", inline = False)

        e.set_image(url = await upload_asset(self.bot, file))
        await interaction.response.send_message(embed = e)

    # /calculate
    @app_commands.command(name = "calculate", description = "Calculates the remaining XP and cooldown to reach a level.")
    @app_commands.describe(target = "The target level to reach", member = "Member to calculate the target XP for, defaults to user")
    async def calculate(self, interaction: discord.Interaction, target: int, member: discord.Member | None = None):

        member = member or interaction.user # type: ignore

        guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore

        current_xp, level, prestige, intro_text, birthday, country = await users.get_user(member.id) # type: ignore

        if (current_xp == None) or (level == None):
            
            await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"Could not fetch XP info about this member.", bot = self.bot), ephemeral = True)
            return

        mention = member.mention # type: ignore

        multiplier_role_id, multiplier = await xp.get_member_highest_multiplier(member)
        multipler_role = guild.get_role(multiplier_role_id) # type: ignore

        target_xp = xp.xp_required(target)
        remaining_xp = target_xp - current_xp

        xp_per_message = [int(XP_MIN * multiplier), int(XP_MAX * multiplier)]
        messages_left = [int(remaining_xp / xp_per_message[0]), int(remaining_xp / xp_per_message[1])]
        average_messages_left = int(np.average(messages_left))

        cooldown_remaining = XP_COOLDOWN * average_messages_left

        def format_seconds(seconds: int) -> str:

            minutes_total = seconds / 60
            days = int(minutes_total // (24 * 60))
            minutes_total -= days * 24 * 60

            hours = int(minutes_total // 60)
            minutes_total -= hours * 60

            # minutes can be half
            minutes = minutes_total

            parts = []
            if days: parts.append(f"**`{days}`** days, ")
            if hours: parts.append(f"**`{hours}`** hours, ")

            if minutes:

                if minutes.is_integer(): parts.append(f"**`{int(minutes)}`** minutes")
                else: parts.append(f"**`{minutes:.1f}`** minutes")

            return " ".join(parts) or "0m"

        percentage = (current_xp / target_xp) * 100
        
        top_colored_role = get_top_colored_role(member) # type: ignore

        if top_colored_role: 

            role_hexes = [f"{top_colored_role.color.value:06X}"] # default if no gradient # type: ignore
            if top_colored_role.secondary_color: role_hexes.append(f"#{top_colored_role.secondary_color.value:06X}") # type: ignore
            if top_colored_role.tertiary_color: role_hexes.append(f"#{top_colored_role.tertiary_color.value:06X}") # type: ignore
    
        else:

            role_hexes = [f"{DEFAULT_COLOR.value:06X}"]

        buffer = self.generate_progress_gradient(int(percentage), role_hexes)
        file = discord.File(buffer, filename = "calculate_bar.png")

        # Generate embed
        e = discord.Embed(title = f"XP Calculator", color = DEFAULT_COLOR, timestamp = datetime.now(), description = f"{mention} **XP Calculate** for Level **{target}**")
        e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

        e.add_field(name = "✨ Current XP", value = f"`{current_xp:,}` (Level **{level}**)", inline = True)
        e.add_field(name = "🎯 Target XP", value = f"`{target_xp:,}`", inline = True)

        if target_xp > current_xp:

            e.add_field(name = "⏩ Remaining XP", value = f"`{remaining_xp:,}`", inline = True)

            e.add_field(name = "🧮 XP per message", value = f"`{xp_per_message[0]}` - `{xp_per_message[1]}`", inline = True)
            e.add_field(name = "💬 Messages remaining", value = f"`{messages_left[1]:,}` - `{messages_left[0]:,}` (average of `{average_messages_left:,}`)")
            e.add_field(name = "🕓 Cooldown remaining", value = format_seconds(cooldown_remaining))

            e.add_field(name = "📊 Percentage Bar", value = f"`{round(percentage, 2)}%`", inline = False) 
        
        else:

            e.add_field(name = "⏩ Remaining XP", value = f"Already reached!", inline = True)
            e.add_field(name = "📊 Percentage Bar", value = f"`{round(percentage, 2)}%`", inline = False) 

            e.description = f"{mention} **XP Calculate** for Level **{target}** (Reached!)"

        e.set_image(url = await upload_asset(self.bot, file))
        await interaction.response.send_message(embed = e)

    # /prestige-shop

    # /black-tie
    @app_commands.command(name = "black-tie", description = "See your progress towards Black Tie.")
    @app_commands.describe(member = "The member to get black tie infomation of", sync = "Optional sync of roles through this command")
    async def black_tie(self, interaction: discord.Interaction, member: discord.Member | None = None, sync: bool = False):
        
        try:

            guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore

            if member and not is_moderator(interaction.user): # type: ignore

                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"`member` can only be set by {guild.get_role(MOD_ROLE).mention} and above only.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
                return
            
            member = member or interaction.user # type: ignore
            mention = member.mention # type: ignore

            red_roles = [guild.get_role(r) for r in [1140051191858999296, 1237874944445124761, 1237465605230035056, 1140058151127887893]] # type: ignore
            orange_roles = [guild.get_role(r) for r in [1140058044215066734, 1153753060280127620, 1153753401935544371, 1238511692166467636, 1259540433713758228]] # type: ignore
            yellow_roles = [guild.get_role(r) for r in [1140057537601880234, 1140057782335315988, 1155092295922753627, 1240726186175369408, 1237465948055933059, 1469827589370675362, 1237856492695326831]] # type: ignore
            green_roles = [guild.get_role(r) for r in [1140057941010022451, 1237474304229113908, 1240726293960724580, 1300743802608156762, 1140051007888437338,1140051051463049286]] # type: ignore
            blue_roles = [guild.get_role(r) for r in [1237465819450179674, 1237473082923286528, 1186250517698064486, 1240726353351933972, 1255272111166198000]] # type: ignore
            purple_roles = [guild.get_role(r) for r in [1153738744600469635, 1174358352751513670, 1240003021430194187, 1469489743946584094, 1237474170624016527]] # type: ignore
            monochrome_roles = [guild.get_role(r) for r in [1237475644150124604, 1166292797570175007, 1202922911384469536, 1241356168475971594, 1242801634820493362]] # type: ignore

            customs = []

            col_map = {"red": red_roles, "orange": orange_roles, "yellow": yellow_roles, "green": green_roles, "blue": blue_roles, "purple": purple_roles, "monochrome": monochrome_roles}
            completed = {"red": False, "orange": False, "yellow": False, "green": False, "blue": False, "purple": False, "monochrome": False}
            emoji = {"red": "🔴", "orange": "🟠", "yellow": "🟡", "green": "🟢", "blue": "🔵", "purple": "🟣", "monochrome": "⚫/⚪"}

            for (role_id, user_id, tie_color) in await reward_roles.get_all_customs():

                if (member.id == user_id): # type: ignore

                    customs.append(role_id)
                    col_map.get(tie_color).append(guild.get_role(role_id)) # type: ignore

            black_tie_role = guild.get_role(1239882669383487508) # type: ignore

            e = discord.Embed(title = f"Black Tie Progression", color = DEFAULT_COLOR, timestamp = datetime.now(), description = f"This shows the progression {mention} has towards obtaining Black Tie.") # type: ignore 
            e.set_author(name = f"BotLobs", icon_url = self.bot.user.display_avatar.url) # type: ignore

            completed_pathways_str = ""

            for col, roles_list in col_map.items():
            
                roles_str = ""
                count = 0
                extras = 0

                roles_str += "\n"

                for role in roles_list:
                           
                    roles_str += f"> {role.mention} | {"✅" if role in member.roles else "❌"} {" (**custom**)" if role.id in customs else ""}\n" # type: ignore
                    if role in member.roles: count += 1
                    if role in customs: extras += 1 

                if count >= 5:
                    roles_str += f"__**✨ Black Tie achieved for this pathway!**__\n" # type: ignore
                    completed_pathways_str += f"\n> **{col.title()}** `{emoji[col]}` ✅"
                    completed[col] = True
                
                else:
                    completed_pathways_str += f"\n> **{col.title()}** `{emoji[col]}` ❌"
                    completed[col] = False

                
                e.add_field(name = f"`{emoji[col]}` {col.title()} Pathway | ({count}/{len(roles_list) + extras}) obtained 🎯", value = roles_str, inline = False)
            
            e.add_field(name = "Completed Pathways", value = completed_pathways_str, inline = False)

            # Sync
            if sync and black_tie_role not in member.roles: # type: ignore

                if any(completed.values()):

                    e.add_field(name = "Sync Roles", value = f"{black_tie_role.mention} added to {member.mention} roles.") # type: ignore
                    await member.add_roles(black_tie_role) # type: ignore

            elif sync and black_tie_role in member.roles: # type: ignore

                e.add_field(name = "Sync Roles", value = f"{black_tie_role.mention} already in {member.mention} roles.") # type: ignore
            
            await interaction.response.send_message(embed = e, allowed_mentions = discord.AllowedMentions(roles = True))
    
        except BaseException as e:
            print(e)

    # /custom
    @app_commands.command(name = "custom", description = "Modify your custom's color, name, or associated icon")
    @app_commands.describe(role = "The custom to modify", name = "The name of the custom, optional", hexes = "Either a single hex like #0f0f0f, or formatted in a comma-separated list like [#0f0f0f,#1f1f1f], optional", color = "The black tie color pathway this custom is on, optional", icon = "The role icon, optional")
    async def custom(self, interaction: discord.Interaction, role: discord.Role, name: str | None = None, color: str | None = None, hexes: str | None = None, icon: discord.Attachment | None = None):
        
        try:

            guild = self.bot.get_guild(int(GUILD_ID)) # type: ignore
            gen_cog = self.bot.get_cog("GeneralCommands")
            member = interaction.user # type: ignore

            hexes_list = []
            file = None

            customs_list = await reward_roles.get_all_customs()

            if role.id not in [c[0] for c in customs_list]: # type: ignore
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{role.mention} is not a custom. To view information, use `/role: role={role.name}`", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
                return

            if icon and not ("ROLE_ICONS" in interaction.guild.features): # type: ignore
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"The server currently doesnt have server icons unlocked. Please don't provide a role icon.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
            
            if role not in member.roles: # type: ignore
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{role.mention} does not belong to you. To view information, use `/role: role={role.name}`", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
                return

            if hexes:

                try:

                    hexes_list = gen_cog.parse_colors(hexes, max_colors = 2) # type: ignore

                    if not ("ENHANCED_ROLE_COLORS" in interaction.guild.features) and len(hexes_list) > 1: # type: ignore
                        await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"The server currently doesn't have gradient roles unlocked. Please input a single hex.", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True)) # type: ignore
                        return

                except ValueError as e:

                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True)
                    return
            
            if color:
                
                colors_list = ["red", "orange", "yellow", "green", "blue", "purple", "monochrome"]

                if color not in colors_list:
                        
                    await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"`color` must be in {', '.join([f"`{c}`" for c in colors_list])}", bot = self.bot), ephemeral = True)
                    return

                else:

                    await reward_roles.remove_custom(role.id)
                    await reward_roles.add_custom(role.id, member.id, tie_color = color)
            
            rgbs_list = [gen_cog.hex_to_rgb(h) for h in hexes_list] if hexes_list else [] # type: ignore
            icon_binary = None

            try:

                icon_binary = await get_icon_binary(icon)
            
            except ValueError as e:
                
                await interaction.response.send_message(embed = basic_embed(title = "Error Encountered!", description = f"{e}", bot = self.bot), ephemeral = True, allowed_mentions = discord.AllowedMentions(roles = True))

            role_icon = io.BytesIO(icon_binary) if icon_binary else None
            role_file = discord.File(role_icon, filename = "custom_icon.png") if icon_binary else None # type: ignore

            await role.edit(name = name if name else role.name, 
                            color = discord.Color.from_rgb(*rgbs_list[0]) if hexes else role.color,
                            secondary_color = discord.Color.from_rgb(*rgbs_list[1]) if hexes and len(rgbs_list) > 1 else role.secondary_color, # type: ignore
                            display_icon = icon_binary if role_icon else None)

            if not role.icon: 

                buffer = gen_cog.generate_color_image((1024, 256), hexes_list = hexes_list if hexes_list else [f"{role.color.value:06X}"]) # type: ignore
                file = discord.File(buffer, filename = "role_color.png")

            await interaction.response.send_message(embed = basic_embed(title = "Custom Editor", description = f"{role.mention} edited for {member.mention} \n> - **Name**: {name if name else role.name}\n> - **Role Color(s)**: {', '.join(hexes_list) if hexes_list else f"{role.color.value:06X}"}\n> - **Black Tie Color**: `{color if color else (await reward_roles.get_custom(role.id))[2]}`", bot = self.bot, thumbnail = (await upload_asset(self.bot, role_file)) if role_icon else await (upload_asset(self.bot, file)))) # type: ignore
        
        except BaseException as e:

            print(e)