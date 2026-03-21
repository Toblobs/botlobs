# cogs > utils > edit_image.py // @toblobs // 21.03.26

from __init__ import *

from .embeds import basic_embed
import asyncio
import uuid
import aiohttp
import os
import re
from typing import List

def parse_rgb(value: str):
    
    _value = value.lower().split()

    channels = []
    if len(_value) != 3:
        return ["R", "G", "B"]  # default full invert

    if _value[0] == "r": channels.append("R")
    if _value[1] == "g": channels.append("G")
    if _value[2] == "b": channels.append("B")

    return channels or ["R", "G", "B"]

## duplicate code

def parse_colors(text: str, max_colors: int = 8) -> List[str]:
        
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
    
def blur_cmd(infile, outfile, value):
    
    value = max(0, min(100, int(value)))
    return f"convert /data/{infile} -blur 0x{value/10} /data/{outfile}"

def sharpen_cmd(infile, outfile, value):
    
    value = max(0, min(100, int(value)))
    return f"convert /data/{infile} -sharpen 0x{value/10} /data/{outfile}"

def monochrome_cmd(infile, outfile, value):
    
    hex1, hex2 = parse_colors(value, max_colors = 2)
    
    if not hex1.startswith("#"): hex1 = "#" + hex1
    if not hex2.startswith("#"): hex2 = "#" + hex2
    
    return f"convert /data/{infile} -colorspace gray -size 256x1 gradient:{hex1}-{hex2} -clut /data/{outfile}"

def invert_cmd(infile, outfile, value):
    
    channels = parse_rgb(value)
    
    if channels == ["R", "G", "B"]:
        return f"convert /data/{infile} -negate /data/{outfile}"
    
    channel_str = ",".join(channels)
    return f"convert /data/{infile} -channel {channel_str} -negate +channel /data/{outfile} "

def hue_cmd(infile, outfile, value):
    
    value = max(0, min(100, int(value)))
    hue = int((value / 255) * 200)
    
    return f"convert /data/{infile} -modulate 100,100,{hue} /data/{outfile}"

def get_edit_command(input_file, output_file, operation, value):
    
    op = operation.lower()
    
    match op:
        
        case "blur": return blur_cmd(input_file, output_file, value)
        case "sharpen": return sharpen_cmd(input_file, output_file, value)
        case "monochrome": return monochrome_cmd(input_file, output_file, value)
        case "invert": return invert_cmd(input_file, output_file, value)
        case "hue": return hue_cmd(input_file, output_file, value)
        case _: return None
        
