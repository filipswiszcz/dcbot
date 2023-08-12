import asyncio, functools, itertools
from async_timeout import timeout

import discord, yt_dlp
from discord.ext import commands

yt_dlp.utils.bug_reports_message = lambda: ""


class VoiceChannelException(Exception):
    """Raised when raised"""
    pass

class StreamException(Exception):
    """Raised when failed to get or process request"""
    pass


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
    
    def cog_unload(self):
        for state in self._states.values():
            self.bot.loop.create_task(state.stop())

    def cog_check(self, ctx: commands.Context):
        if not ctx.guild:
            raise commands.NoPrivateMessage("This command can't be used in private channels.")
        return True
    
    async def cog_before_invoke(self, ctx: commands.Context):
        #return super().cog_before_invoke(ctx)
        ctx.voice_state = self._get_state(ctx)

    async def cog_command_error(self, ctx: commands.Context, error: commands.CommandError):
        await ctx.send(f"An error occurred: {str(error)}")
    
    """@commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        print("Message content: ", message.content)
        await message.edit(
            content=":edited",
            embed=None,
            embeds=[],
            attachments=[],
            suppress=True
        )"""
    
    @commands.command(name="join")
    async def _join(self, ctx: commands.Context):
        """ Joins a voice channel """

        channel = ctx.author.voice.channel
        if ctx.voice_state.voice_channel:
            await ctx.voice_state.voice_channel.move_to(channel); return
        
        ctx.voice_state.voice_channel = await channel.connect()
    
    @commands.command(name="play")
    async def _play(self, ctx: commands.Context, *, search: str):
        """Joins a voice channel and starts to stream a song"""

        if not ctx.voice_state.voice_channel:
            await ctx.invoke(self._join)

        await ctx.send("Searching for a song.")
        try:
            source = await _YouTube.prepare_source(ctx, search, loop=self.bot.loop)
        except StreamException:
            await ctx.send("An error occurred while processing this request.")
        else:
            song = Song(source)
            await ctx.voice_state.queued_songs.put(song)

            if ctx.voice_state.active:
                await ctx.send(f"Added to queue: {str(source)}")
            else: await ctx.send(f"Now streaming: {str(source)}")

    @commands.command(name="skip")
    async def _skip(self, ctx: commands.Context):
        """Skip a current playing song"""

        if not ctx.voice_state.active:
            return await ctx.send("Sirius is not playing any song at the moment.")
        
        ctx.voice_state.skip()

    @commands.command(name="pause")
    async def _pause(self, ctx: commands.Context):
        """Pauses a current playing song"""

        if ctx.voice_state.active and ctx.voice_state.voice_channel.is_playing():
            ctx.voice_state.voice_channel.pause()
            await ctx.send("Paused the stream.")

    @commands.command(name="resume")
    async def _resume(self, ctx: commands.Context):
        """Resumes a paused song"""

        if ctx.voice_state.active and ctx.voice_state.voice_channel.is_paused():
            ctx.voice_state.voice_channel.resume()
            await ctx.send("Resumed the stream.")

    @commands.command(name="stop")
    async def _stop(self, ctx: commands.Context):
        """Stops streaming after a current song and clears a queue"""

        if not ctx.voice_state.voice_channel:
            return await ctx.send("Sirius is not connected to any voice channel.")
        
        ctx.voice_state.queued_songs.clear()

        if not ctx.voice_state.active:
            ctx.voice_state.voice_channel.stop()
            await ctx.send("End of stream. Till the next time!")
        else: await ctx.send("Stream will stop after this song.")

    @commands.command(name="leave")
    async def _leave(self, ctx: commands.Context):
        """Leaves the voice channel and clears a queue if present"""

        if not ctx.voice_state.voice_channel:
            return await ctx.send("Sirius is not connected to any voice channel.")
        
        await ctx.voice_state.stop()
        del self._states[ctx.guild.id]

        await ctx.send("End of stream. Till the next time!")

    @_join.before_invoke
    @_play.before_invoke
    async def ensure_voice_state(self, ctx: commands.Context):
        if not ctx.author.voice or not ctx.author.voice.channel:
            raise commands.CommandError("You are not connected to any voice channel.")
        if ctx.voice_client:
            if ctx.voice_client.channel != ctx.author.voice.channel:
                raise commands.CommandError("Siurius is already in the voice channel.")


class State:
    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self._ctx = ctx

        self.current_song = None
        self.next_song = asyncio.Event()
        self.voice_channel = None
        self.queued_songs = _Playlist()

        self._loop = False
        self.queue_loop = bot.loop.create_task(self.__queue_loop_task())
        self._volume = 1
        self.skip_votes = set()

    def __del__(self):
        self.queue_loop.cancel()

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
    def active(self) -> bool:
        return self.voice_channel and self.current_song
    
    def next(self, error=None):
        if error:
            raise VoiceChannelException(str(error))
        self.next_song.set()

    def skip(self):
        self.skip_votes.clear()
        if self.active:
            self.voice_channel.stop()
    
    async def stop(self):
        self.queued_songs.clear()
        if self.voice_channel:
            await self.voice_channel.disconnect()
            self.voice_channel = None

    async def __queue_loop_task(self):
        while True:
            self.next_song.clear()

            if not self.loop:
                try:
                    async with timeout(120):
                        self.current_song = await self.queued_songs.get()
                except asyncio.TimeoutError:
                    self.bot.loop.create_task(self.stop())
                    return
                                
            self.current_song.source.volume = self._volume
            self.voice_channel.play(self.current_song.source, after=self.next)
            await self.next_song.wait()


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
    __slots__ = ("source", "request_author")

    def __init__(self, source: _YouTube):
        self.source = source
        self.request_author = source._request_author


async def setup(bot):
    await bot.add_cog(Music(bot))
