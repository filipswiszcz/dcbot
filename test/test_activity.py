import pytest

import discord
import discord.ext.test as dpytest


@pytest.mark.asyncio
async def test_verify_activity(bot):
    streaming = discord.Activity(
        name="Streaming",
        type=discord.ActivityType.streaming,
        url="https://twitch.com"
    )

    await bot.change_presence(activity=streaming)
    assert dpytest.verify().activity().matches(streaming)

    playing = discord.Activity(
        name="Playing",
        type=discord.ActivityType.playing,
    )

    await bot.change_presence(activity=playing)
    assert dpytest.verify().activity().matches(playing)
    

@pytest.mark.asyncio
async def test_verify_no_activity(bot):
    await bot.change_presence(activity=None)
    assert dpytest.verify().activity().matches(None)