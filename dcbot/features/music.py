import asyncio
import functools
import itertools

from async_timeout import timeout

from discord import (
    PCMVolumeTransformer,
    FFmpegPCMAudio
)
from discord.ext import commands

from yt_dlp import utils, YoutubeDL

from dcbot.constants import NAME


utils.bug_reports_message = lambda: ""


class VoiceChannelException(Exception):
    """ Raised when there is a problem with voice channel """


class StreamException(Exception):
    """ Raised when failed to get or process request """
    pass


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.__states = {}

    def __init_state(self, ctx: commands.Context):
        state = self.__states.get(ctx.guild.id)
        if not state:
            state = _State(self.bot, ctx)
            self.__states[ctx.guild.id] = state
        return state

    async def cog_before_invoke(self, ctx: commands.Context):
        ctx.voice_state = self.__init_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send(f"An error occurred: {str(error)}")

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Initialized music feature.")

    @commands.command(name="join", aliases=["j"])
    async def _join(self, ctx: commands.Context):
        """ Joins a voice channel """

        channel = ctx.author.voice.channel
        if ctx.voice_state.voice_channel:
            await ctx.voice_state.voice_channel.move_to(channel); return
        
        ctx.voice_state.voice_channel = await channel.connect()

    @commands.command(name="play", aliases=["p"])
    async def _play(self, ctx: commands.Context, *, search: str):
        """ Joins a voice channel and starts to stream a song """

        if not ctx.voice_state.voice_channel:
            await ctx.invoke(self._join)

        await ctx.send("Searching for the song..")

        try: source = await _YouTube.prepare_source(ctx, search, loop=self.bot.loop)
        except StreamException:
            await ctx.send("An error occurred, while processing the request.")
        else:
            song = _Song(source)
            await ctx.voice_state.queued_songs.put(song)

            if ctx.voice_state.is_active():
                await ctx.send(f"Added to the queue: {str(source)}")
            else: await ctx.send(f"Now streaming: {str(source)}")

    @commands.command(name="skip")
    async def _skip(self, ctx: commands.Context):
        """ Skip a current playing song """

        if not ctx.voice_state.is_active():
            return await ctx.send(f"{NAME} is not playing any song at the moment.")
        
        ctx.voice_state.skip()

    @commands.command(name="pause")
    async def _pause(self, ctx: commands.Context):
        """ Pauses a current playing song """

        if ctx.voice_state.is_active() and ctx.voice_state.voice_channel.is_playing():
            ctx.voice_state.voice_channel.pause()
            await ctx.send("Paused the stream.")

    @commands.command(name="resume")
    async def _resume(self, ctx: commands.Context):
        """ Resumes a paused song """

        if ctx.voice_state.is_active() and ctx.voice_state.voice_channel.is_paused():
            ctx.voice_state.voice_channel.resume()
            await ctx.send("Resumed the stream.")

    @commands.command(name="stop")
    async def _stop(self, ctx: commands.Context):
        """ Stops streaming after a current song and clears a queue """

        if not ctx.voice_state.voice_channel:
            return await ctx.send(f"{NAME} is not connected to any voice channel.")
        
        ctx.voice_state.queued_songs.clear()

        if not ctx.voice_state.is_active():
            ctx.voice_state.voice_channel.stop()
            await ctx.send("End of stream. Till the next time!")
        else: await ctx.send("Stream will stop after this song.")

    @commands.command(name="leave")
    async def _leave(self, ctx: commands.Context):
        """ Leaves the voice channel and clears a queue if present """

        if not ctx.voice_state.voice_channel:
            return await ctx.send(f"{NAME} is not connected to any voice channel.")
        
        await ctx.voice_state.stop()
        del self.__states[ctx.guild.id]

        await ctx.send("End of stream. Till the next time!")

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError("You are not connected to any voice channel.")
        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError(f"{NAME} is already connected to the voice channel.")

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage("The command cannot be used in private conversations.")
        return True

    def cog_unload(self):
        for state in self.__states.values():
            self.bot.loop.create_task(state.stop())


class _State:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx
        self.curr_song = None
        self.next_song = asyncio.Event()
        self.voice_channel = None
        self.queued_songs = _Playlist()
        self.__loop = False
        self.queue_loop = bot.loop.create_task(self.__queue_loop_task())
        self.volume = 1
        self.skip_votes = set()

    def __del__(self):
        self.queue_loop.cancel()

    async def __queue_loop_task(self):
        while True:
            self.next_song.clear()
            if not self.get_loop():
                try:
                    async with timeout(300):
                        self.curr_song = await self.queued_songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop()); return

            self.curr_song.source.volume = self.volume
            self.voice_channel.play(self.curr_song.source, after=self.next)
            
            await self.next_song.wait()

    def get_loop(self):
        return self.__loop

    def set_loop(self, status: bool):
        self.__loop = status

    def is_active(self):
        return self.voice_channel and self.curr_song

    def next(self, error=None):
        if error: pass
        self.next_song.set()

    def skip(self):
        self.skip_votes.clear()
        if self.is_active():
            self.voice_channel.stop()

    async def stop(self):
        self.queued_songs.clear()
        if self.voice_channel:
            await self.voice_channel.disconnect()
            self.voice_channel = None


class _YouTube(PCMVolumeTransformer):

    ytdl_params = {
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

    ffmpeg_params = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
    }

    ytdl = YoutubeDL(ytdl_params)

    def __init__(self, ctx: commands.Context, source: FFmpegPCMAudio, *, data: dict, volume: float=1):
        super().__init__(source, volume)
        self._requester = ctx.author
        self._channel = ctx.channel
        self._data = data
        self.__title = data.get("title")
        self.__uploader = data.get("uploader")

    def __str__(self):
        return f"[{self.__title}] by {self.__uploader}"

    @classmethod
    async def prepare_source(cls, ctx: commands.Context, search: str, *, loop: asyncio.BaseEventLoop=None):
        loop = loop or asyncio.get_event_loop()
        part = functools.partial(cls.ytdl.extract_info, search, download=False, process=False)
        a = await loop.run_in_executor(None, part)

        if a is None: raise Exception
        if "entries" not in a: b = a
        else:
            b = None
            for entry in a["entries"]:
                if entry: b = entry; break
            if b is None: raise Exception

        url = b["webpage_url"]
        part = functools.partial(cls.ytdl.extract_info, url, download=False)
        c = await loop.run_in_executor(None, part)

        if "entries" not in c: d = c
        else:
            d = None
            while d is None:
                try:
                    d = c["entries"].pop(0)
                except IndexError: raise Exception

        return cls(ctx, FFmpegPCMAudio(d["url"], **cls.ffmpeg_params), data=d)


class _Playlist(asyncio.Queue):

    def __getitem__(self, item):
        if isinstance(item, slice):
            return list(itertools.islice(self._queue, item.start, item.stop, item.step))
        else: return self._queue[item]

    def __iter__(self):
        return self._queue.__iter__()

    def __len__(self):
        return self.qsize()

    def clear(self):
        self._queue.clear()

    def shuffle(self):
        from random import shuffle
        shuffle(self._queue)

    def remove(self, index):
        del self._queue[index]


class _Song:
    __slots__ = ("source", "requester")

    def __init__(self, source: _YouTube):
        self.source = source
        self.requester = source._requester