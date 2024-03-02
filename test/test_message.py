import pytest

import discord
import discord.ext.test as dpytest


@pytest.mark.asyncio
async def test_messasge(bot):
    guild = bot.guilds[0]
    author = guild.members[0]
    channel = guild.channels[0]
    image = discord.Attachment(
        state=dpytest.back.get_state(),
        data=dpytest.back.facts.make_attachment_dict(
            "rocket.jpg",
            15112122,
            "https://media.discordapp.net/attachments/some_number/random_number/rocket.jpg",
            "https://media.discordapp.net/attachments/some_number/random_number/rocket.jpg",
            height=1000,
            width=1000,
            content_type="image/jpeg"
        )
    )
    data = dpytest.back.facts.make_message_dict(channel, author, attachments=[image])

    try: discord.Message(state=dpytest.back.get_state(), channel=channel, data=data)
    except Exception as exc: pytest.fail(str(exc))


@pytest.mark.asyncio
async def test_message_edit(bot):
    guild = bot.guilds[0]
    channel = guild.channels[0]

    msg = await channel.send("test message")
    pers_msg_a = await channel.fetch_message(msg.id)
    edited_msg = await msg.edit(content="edited test message")
    pers_msg_b = await channel.fetch_message(msg.id)

    assert edited_msg.content == "edited test message"
    assert pers_msg_a.content == "test message"
    assert pers_msg_b.content == "edited test message"