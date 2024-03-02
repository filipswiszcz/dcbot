import pytest

import discord.ext.test as dpytest


@pytest.mark.asyncio
async def test_add_reaction(bot):
    guild = bot.guilds[0]
    channel = guild.text_channels[0]

    message = await channel.send("test message")
    await message.add_reaction("😂")
    message = await channel.fetch_message(message.id)

    assert len(message.reactions) == 1


@pytest.mark.asyncio
async def test_remove_reaction(bot):
    guild = bot.guilds[0]
    channel = guild.text_channels[0]

    message = await channel.send("test message")
    await message.add_reaction("😂")
    await message.remove_reaction("😂", guild.me)
    message = await channel.fetch_message(message.id)

    assert len(message.reactions) == 0


@pytest.mark.asyncio
async def test_user_add_reaction(bot):
    guild = bot.guilds[0]
    channel = guild.text_channels[0]
    member = guild.members[0]

    message = await channel.send("test message")
    await dpytest.add_reaction(member, message, "😂")
    message = await channel.fetch_message(message.id)
    reaction = message.reactions[0]

    assert reaction.emoji == "😂"
    assert reaction.me is False


@pytest.mark.asyncio
async def test_user_remove_reaction(bot):
    guild = bot.guilds[0]
    channel = guild.text_channels[0]
    member = guild.members[0]

    message = await channel.send("test message")
    await message.add_reaction("😂")
    await dpytest.add_reaction(member, message, "😂")
    await dpytest.remove_reaction(member, message, "😂")
    message = await channel.fetch_message(message.id)
    reaction = message.reactions[0]

    assert reaction.emoji == "😂"
    assert reaction.count == 1
    assert reaction.me is True