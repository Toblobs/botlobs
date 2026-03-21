# cogs > utils > music.py // @toblobs // 21.03.26

from __init__ import *

import yt_dlp
import asyncio
import spotipy

from .embeds import basic_embed

MUSIC_CHANNEL = 1481329423738343656

ytdl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
    "extract_flat": False,
    "ignoreerrors": True,
    "nocheckcertificate": True,
    "geo_bypass": True,
    "simulate": False,
    "noprogress": True,
    "js_runtimes": {"node": {}},  # Required for some YouTube extraction
}

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5", 
    "options": "-vn -c:a libopus -b:a 192k"
}

ytdl = yt_dlp.YoutubeDL(ytdl_opts) # type: ignore

CONTROLS = ["⏯", "⏭", "⏹", "🔁", "📜"]

class Song:
    
    def __init__(self, info):
        
        self.title = info["title"]
        self.url = info["webpage_url"]
        self.info = info

async def extract_song(query):
    
    loop = asyncio.get_event_loop()

    info = await loop.run_in_executor(
        None,
        lambda: ytdl.extract_info(f"ytsearch:{query}", download=False)
    )

    if not info:
        raise Exception("yt-dlp failed to extract the track")

    if "entries" in info:
        
        entries = [e for e in info["entries"] if e] # type: ignore
        
        if not entries:
            raise Exception("No valid results found")
        
        info = entries[0]

    return Song(info)

def is_spotify(url): return "spotify.com/track" in url

def spotify_to_query(sp: spotipy.Spotify, url: str):
    
    track = sp.track(url)
    name = track["name"] # type: ignore
    artists = ", ".join(a["name"] for a in track["artists"]) # type: ignore
    
    return f"{name} {artists}"

players = {}

class MusicPlayer: 
    
    def __init__(self, bot: commands.Bot, guild: discord.Guild):
        
        self.bot = bot
        self.guild = guild
        
        self.queue = asyncio.Queue()
        
        self.current = None
        self.loop = False
        
        self.controller = None
        
        self.next = asyncio.Event()
        self.task = bot.loop.create_task(self.player_loop())
    
    async def player_loop(self):
        
        def after_playback(error):
            
            if error: print(f"[FFMPEG ERROR] {error}")
            self.bot.loop.call_soon_threadsafe(self.next.set)
        

        await self.bot.wait_until_ready()
        
        while True:
            
            self.next.clear()
            
            try: song = await asyncio.wait_for(self.queue.get(), timeout = 300)
            
            except asyncio.TimeoutError:
                
                vc: discord.VoiceClient = self.guild.voice_client # type: ignore
                if vc: await vc.disconnect(force = True)
                
                players.pop(self.guild.id, None)
                return
        
            self.current = song
            
            info = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(song.url, download = False))

            if not info:
                self.next.set()
                continue

            stream_url = info.get("url")

            if not stream_url:
                self.next.set()
                continue 
            
            source = await discord.FFmpegOpusAudio.from_probe(stream_url, before_options = FFMPEG_OPTIONS["before_options"], options = FFMPEG_OPTIONS["options"])

            vc: discord.VoiceClient = self.guild.voice_client # type: ignore
            if not vc: return
            
            if vc.is_playing(): 
                vc.stop()
                await asyncio.sleep(0.1)
            
            self.next.clear()
            
            vc.play(source, after = after_playback)
            
            async def watchdog():
                
                while True:
                    await asyncio.sleep(2)
                    
                    vc: discord.VoiceClient = self.guild.voice_client # type: ignore
                    
                    if not vc:
                        self.next.set()
                        return
                    
                    if not vc.is_playing() and not vc.is_paused():
                        self.next.set()
                        return
            
            self.bot.loop.create_task(watchdog())
            
            await self.update_controller()
            await self.next.wait()
            
            if self.loop: await self.queue.put(song)
            
    async def update_controller(self):
        
        if not self.controller: return
        
        if not self.current: e = basic_embed(title = "🎵 Music Controller", description = f"Nothing playing yet...", bot = self.bot) # type: ignore
        else: e = basic_embed(title = "🎵 Now Playing", description = f"**{self.current.title}**", bot = self.bot) # type: ignore
        
        e.add_field(name = "Controls", value = "⏯ Pause | ⏭ Skip | ⏹ Stop | 🔁 Loop | 📜 Queue", inline = False)
        await self.controller.edit(embed = e) # type: ignore
        
def get_player(bot: commands.Bot, guild: discord.Guild):
    
    if guild.id not in players: players[guild.id] = MusicPlayer(bot, guild)
    return players[guild.id]

        
        
        