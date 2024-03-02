import pytest

import discord
import discord.ext.test as dpytest


@pytest.mark.asyncio
async def test_create_voice_channel(bot):
    guild = bot.guilds[0]; self = guild
    name = "voice_channel_1"
    
    channel = await bot.http.create_channel(guild, channel_type=discord.ChannelType.voice.value)

    assert channel["type"] == discord.ChannelType.voice
    assert channel["name"] == name


@pytest.mark.asyncio
async def test_make_voice_channel(bot):
    guild = bot.guilds[0]
    
    channel = dpytest.backend.make_voice_channel("voice", guild, bitrate=100, user_limit=5)

    assert channel.name == "voice"
    assert channel.guild == guild
    assert channel.bitrate == 100
    assert channel.user_limit == 5