import asyncio
import functools

from discord.ext import commands
import discord
import yt_dlp

yt_dlp.utils.bug_reports_message = lambda: ""


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="join")
    async def join(self, ctx: commands.Context):
        """ Joins a voice channel """

        channel = ctx.author.voice.channel
        #TODO check if bot is already connected
        await channel.connect()

    @commands.command(name="play")
    async def play(self, ctx: commands.Context, *, search: str):
        """ Streaming a song to the voice channel """

        await ctx.send("Searching for a song.")
        try:
            source = await _YouTube.prepare_source(ctx, search, loop=self.bot.loop)
        except Exception as e:
            await ctx.send(f"An error occurred while processing this request. {e}")
        else:
            song = Song(source)
            #await ctx.send(f"Added to queue {str(source)}.")
            await ctx.send(f"Now playing: {str(source)}")
            ctx.voice_client.play(source, after=lambda e: print(f"end of song: {str(source)}"))


class _YouTube(discord.PCMVolumeTransformer):

    ytdl_format_options = {
        "format": "bestaudio/best",
        "extractaudio": True,
        "audioformat": "mp3",
        "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
        "restrictfilenames": True,
        "noplaylist": True,
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "logtostderr": False,
        "quiet": True,
        "no_warnings": True,
        "default_search": "auto",
        "source_address": "0.0.0.0"
    }

    ffmpeg_options = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
    }

    ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

    def __init__(self, ctx: commands.Context, source: discord.FFmpegPCMAudio, *, data: dict, volume: float = 1):
        super().__init__(source, volume)

        self.__request_author = ctx.author
        self.__channel = ctx.channel

        self.data = data

        self.__title = data.get("title")
        self.__uploader = data.get("uploader")

    def __str__(self):
        return f"[{self.__title}] by {self.__uploader}"
    
    def get_request_author(self):
        return self.__request_author
    
    @classmethod
    async def prepare_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop = None):
        loop = loop or asyncio.get_event_loop()

        partial = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        data = await loop.run_in_executor(None, partial)

        if data is None:
            raise Exception
        
        if "entries" not in data:
            chunk = data
        else:
            chunk = None
            for entry in data["entries"]:
                if entry:
                    chunk = entry; break
                
            if chunk is None:
                raise Exception
            
        url = chunk["webpage_url"]
        partial = functools.partial(cls.ytdl.extract_info, url, download=False)
        other_data = await loop.run_in_executor(None, partial)

        if "entries" not in other_data:
            other_chunk = other_data
        else:
            other_chunk = None
            while other_chunk is None:
                try:
                    other_chunk = other_data["entries"].pop(0)
                except IndexError:
                    raise Exception
                
        return cls(ctx, discord.FFmpegPCMAudio(other_chunk["url"], **cls.ffmpeg_options), data=other_chunk)
    
class Song:
    __slots__ = ("__source", "__request_author")

    def __init__(self, source: _YouTube):
        self.__source = source
        self.__request_author = source.get_request_author()

    def prepare_banner(self):
        #TODO final touch
        pass


async def setup(bot):
    await bot.add_cog(Music(bot))
