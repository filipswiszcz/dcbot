import asyncio, functools, itertools
from async_timeout import timeout

from discord.ext import commands
import discord, yt_dlp

yt_dlp.utils.bug_reports_message = lambda: ""


class VoiceChannelError(Exception):
    """Raised when """
    pass

class StreamError(Exception):
    """Raised when failed to get or process request"""


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._states = {}

    def _get_state(self, ctx: commands.Context):
        state = self._states.get(ctx.guild.id)
        if not state:
            state = State(self.bot, ctx)
            self._states[ctx.guild.id] = state
        return state
    
    @commands.command(name="join")
    async def join(self, ctx: commands.Context):
        """ Joins a voice channel """

        channel = ctx.author.voice.channel
        #TODO check if bot is already connected
        await channel.connect()
    
    @commands.command(name="play")
    async def _play(self, ctx: commands.Context, *, search: str):
        """Joins a voice channel and starts to stream a song"""

        channel = ctx.author.voice.channel
        #if ctx._state._voice_channel:
        #    await ctx._state._voice_channel.move_to(channel); return
        ctx._state._voice_channel = await channel.connect()

        await ctx.send("Searching for a song.")
        try:
            source = await _YouTube.prepare_source(ctx, search, loop=self.bot.loop)
        except Exception as e:
            await ctx.send(f"An error occurred while processing this request. {e}")
        else:
            song = Song(source)
            #await ctx.send(f"Added to queue {str(source)}.")
            await ctx.send(f"Now streaming: {str(source)}")
            ctx.voice_client.play(source, after=lambda e: print(f"end of song: {str(source)}"))

    @commands.command(name="stop")
    async def _stop(self, ctx: commands.Context):
        """Stops streaming a song and clears a queue if present"""

        if not ctx._state._voice_channel:
            return await ctx.send("Sirius is not connected to any voice channel.")
        
        ctx._state._queued_songs.clear()
        if not ctx._state.active:
            ctx._state._voice_channel.stop()
            await ctx.send("End of stream. Till the next time!")

    @commands.command(name="leave")
    async def _leave(self, ctx: commands.Context):
        """Leaves the voice channel and clears a queue if present"""

        if not ctx._state._voice_channel:
            return await ctx.send("Sirius is not connected to any voice channel.")
        
        await ctx._state.stop()
        del self._states[ctx.guild.id]


class State:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self._current_song = None
        self._next_song = asyncio.Event()
        self._voice_channel = None
        self._queued_songs = _Playlist()

        self._loop = False
        self._queue_loop = bot.loop.create_task(self.__queue_loop_task())
        self._volume = 1
        self.skip_votes = ()

    def __del__(self):
        self._queue_loop.cancel()

    @property
    def loop(self):
        return self._loop
    
    @loop.setter
    def loop(self, value: bool):
        self._loop = value

    @property
    def volume(self):
        return self._volume
    
    @volume.setter
    def volume(self, value: float):
        self._volume = value

    @property
    def active(self):
        return self._voice_channel and self._current_song
    
    def next(self, error=None):
        if error:
            raise VoiceChannelError(str(error))
        self._next_song.set()

    def skip(self):
        self.skip_votes.clear()
        if self.active:
            self._voice_channel.stop()
    
    async def stop(self):
        self._queued_songs.clear()
        if self._voice_channel:
            await self._voice_channel.disconnect()
            self._voice_channel = None

    async def __queue_loop_task(self):
        while True:
            self.next.clear()

            if not self._loop:
                try:
                    async with timeout(120):
                        self._current_song = await self._queued_songs.get()
                except asyncio.TimeoutError as e:
                    self.bot.loop.create_task(self.stop()); return
                
            self._current_song._source._channel.volume = self._volume
            self._voice_channel.play(self._current_song._source, after=self.next)
            await self.next.wait()


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

        self._request_author = ctx.author
        self._channel = ctx.channel

        self.data = data

        self.__title = data.get("title")
        self.__uploader = data.get("uploader")

    def __str__(self):
        return f"[{self.__title}] by {self.__uploader}"
    
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


class _Playlist(asyncio.Queue):

    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else:
            return self._queue[item]
        
    def __iter__(self):
        return self._queue.__iter__()
    
    def __len__(self):
        return self.qsize()
    
    def clear(self):
        self._queue.clear()

    def shuffle(self):
        from random import shuffle
        shuffle(self._queue)

    def remove(self, index: int):
        del self._queue[index]

    
class Song:
    __slots__ = ("_source", "_request_author")

    def __init__(self, source: _YouTube):
        self._source = source
        self._request_author = source._request_author


async def setup(bot):
    await bot.add_cog(Music(bot))
