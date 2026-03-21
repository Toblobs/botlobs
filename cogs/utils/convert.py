# cogs > utils > convert.py // @toblobs // 21.03.26

from __init__ import *

from .embeds import basic_embed
from .edit_image import get_edit_command
import asyncio
import uuid
import aiohttp
import os

def get_convert_command(input_ext: str, output_ext: str, infile: str, outfile: str):
    
    input_ext = input_ext.lower()
    output_ext = output_ext.lower()

    VIDEO = {"mp4", "mov", "webm"}
    AUDIO = {"mp3", "wav", "ogg"}
    IMAGE = {"png", "jpg", "jpeg", "webp", "gif"}
    SVG = {"svg"}
    
    if input_ext in VIDEO and output_ext in AUDIO:
        return f"ffmpeg -i /data/{infile} -vn -acodec {output_ext} /data/{outfile}"
    
    if input_ext in VIDEO and output_ext in VIDEO:
        return f"ffmpeg -i /data/{infile} /data/{outfile}"
    
    if input_ext in AUDIO and output_ext in AUDIO:
        return f"ffmpeg -i /data/{infile} /data/{outfile}"
    
    if input_ext in SVG:
        return f"rsvg-convert /data/{infile} -o /data/{outfile}"
    
    if input_ext == "gif" and output_ext in IMAGE:
        return f"convert /data/{infile}[0] /data/{outfile}"
    
    if input_ext in IMAGE and output_ext in IMAGE:
        return f"convert /data/{infile} /data/{outfile}"
    
    return None

async def download_file(url: str, path: str):
    
    async with aiohttp.ClientSession() as session:
        
        async with session.get(url) as resp:

                if resp.status != 200: raise Exception("Download failed")
                
                with open(path, "wb") as f: f.write(await resp.read())
                
def cleanup(*paths):
    
    for p in paths:
        
        try: os.remove(p)
        except: pass

async def run_docker_command(comm, **kwargs):
    
    uid = str(uuid.uuid4())

    input_name = os.path.basename(kwargs["input_path"])
    output_name = f"{uid}.{kwargs["output_ext"]}"
    output_path = os.path.join(CONVERT_PATH, output_name)
    input_ext = input_name.split(".")[-1]
        
    if comm == "convert":

        command = get_convert_command(input_ext, kwargs["output_ext"], input_name, output_name)
        if not command: raise Exception(f"Unsupported conversion: `{input_ext}` → `{kwargs["output_ext"]}`")

    elif comm == "edit-image":
        
        command = get_edit_command(input_name, output_name, kwargs["operation"], kwargs["value"])
        if not command: raise Exception(f"Invalid operation or value: `{kwargs["operation"]}` / `{kwargs["value"]}`")

    cmd = [
        "docker", "run", "--rm",
        "--network", "none",
        "--memory", "512m",
        "--cpus", "1.0",
        "-v", f"{CONVERT_PATH}:/data",
        "file-converter",
        command # type: ignore
    ]
    
    proc = await asyncio.create_subprocess_exec(*cmd, stdout = asyncio.subprocess.PIPE, stderr = asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()
    
    if proc.returncode != 0: raise Exception(stderr.decode())
    return output_path