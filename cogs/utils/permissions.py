# cogs > utils > embeds.py // @toblobs // 18.03.26

from __init__ import *

STAFF_ROLE = 1140049417626464316

JR_MOD_ROLE = 1139119456862339082
MOD_ROLE = 1139119339161784330
ADMIN_ROLE = 1139119232710344784
TOBLOBS_ROLE = 1139118721022046289

staff = [JR_MOD_ROLE, MOD_ROLE, ADMIN_ROLE, TOBLOBS_ROLE]

ELITIST_ROLE = 1140051108778225684
SERVER_BOOSTER_ROLE = 1153738744600469635 

BLOB_ROLE = 1139122746199134249
SUIT_ROLE = 1140049620857266257
SHADES_ROLE = 1140049685885767692
SHADES_PLUS_ROLE = 1140049746908684399
SHADES_PLUS_PLUS_ROLE = 1140049851850162226
CLASSY_ROLE = 1140049921500795141
CLASSY_PLUS_ROLE = 1140049956829405184
MAX_CLASS_ROLE = 1140049990677450802

levels = [BLOB_ROLE, SUIT_ROLE, SHADES_ROLE, SHADES_PLUS_ROLE, SHADES_PLUS_PLUS_ROLE, CLASSY_ROLE, CLASSY_PLUS_ROLE, MAX_CLASS_ROLE]

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
        if member2_staff_roles: highest_member2_role = max(member2_staff_roles, key = lambda x: staff.index(x))

        if highest_member1_role and highest_member2_role:
            
            if staff.index(highest_member1_role) > staff.index(highest_member2_role):
                return True

            else:
                return False

        else:

            return False
            
    else:

        return False

def is_at_least_level(member: discord.Member, role_id: int) -> bool:
    
    if role_id not in levels: return False
    indx = levels.index(role_id)
    
    if any(r.id in levels[indx:] for r in member.roles):
        return True
    
    return False