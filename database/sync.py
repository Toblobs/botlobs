# database > sync.py // @toblobs // 04.03.26

from .__init__ import *

import time
import discord
from .dbio import db
from .xp import *
from .users import get_user_level
from .reward_roles import get_roles_for_level, get_syncable_roles


async def sync_roles(member: discord.Member, level: int, bot: commands.Bot):

    guild = member.guild
    rows = await get_roles_for_level(level)

    syncable_roles = set(await get_syncable_roles())

    member_roles = {r.id for r in member.roles}

    keep_roles = set()
    replace_roles = []

    for role_level, role_id, keep, sync in rows:

        if not sync: continue
        if keep: keep_roles.add(role_id)
        else: replace_roles[role_level] = role_id

    highest_replace = None

    if replace_roles: highest_replace_role = max(replace_roles, key = lambda r: r[0])[1]

    target_roles = set(keep_roles)

    if highest_replace_role: target_roles.add(highest_replace) # type: ignore

    # Roles to add
    add_roles = target_roles - member_roles
    add_roles = [guild.get_role(r) for r in add_roles if guild.get_role(r)]

    # Roles to remove
    remove_roles = (syncable_roles - target_roles) & member_roles
    remove_roles = [guild.get_role(r) for r in remove_roles if guild.get_role(r)]

    # Apply changes
    if add_roles: await member.add_roles(*[member.guild.get_role(r) for r in add_roles]) # type: ignore
    if remove_roles: await member.remove_roles(*[member.guild.get_role(r) for r in remove_roles]) # type: ignore

async def sync_all_roles(bot: commands.Bot):

    guild = bot.get_guild(GUILD_ID) # type: ignore

    if guild:

        for member in guild.members:

            level = await get_user_level(member.id)