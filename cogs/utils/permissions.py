# cogs > utils > embeds.py // @toblobs // 03.03.26

from __init__ import *

JR_MOD_ROLE = 1139119456862339082
MOD_ROLE = 1139119339161784330
ADMIN_ROLE = 1139119232710344784
TOBLOBS_ROLE = 1139118721022046289

staff = [JR_MOD_ROLE, MOD_ROLE, ADMIN_ROLE, TOBLOBS_ROLE]

ELITIST_ROLE = 1140051108778225684

def is_staff(member: discord.Member) -> bool:

    if any(r.id in staff for r in member.roles):
        return True

    return False

def is_moderator(member: discord.Member) -> bool:

    if any(r.id in staff[1:] for r in member.roles):
        return True

    return False

def is_staff_supersede(member1: discord.Member, member2: discord.Member) -> bool:

    if is_staff(member1) and is_staff(member2):
        
        member1_staff_roles = [r.id for r in member1.roles if r.id in staff]
        member2_staff_roles = [r.id for r in member2.roles if r.id in staff]

        highest_member1_role = highest_member2_role = None

        if member1_staff_roles: highest_member1_role = max(member1_staff_roles, key = lambda x: staff.index(x)) 
        if member2_staff_roles: highest_member2_role = max(member1_staff_roles, key = lambda x: staff.index(x))

        if highest_member1_role and highest_member2_role:
            
            if staff.index(highest_member1_role) > staff.index(highest_member2_role):
                return True

            else:
                return False

        else:

            return False
            
    else:

        return False
        