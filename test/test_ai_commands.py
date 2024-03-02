import os
#import asyncio

import pytest

import discord.ext.test as dpytest


@pytest.mark.asyncio
async def test_features_load(bot):
    assert len(bot.cogs) == 2


@pytest.mark.asyncio
async def test_text_assistant(bot):
    await dpytest.message("/ai what is the first rule of fight club?")
    assert not dpytest.verify().message().nothing()


@pytest.mark.asyncio
async def test_image_generator(bot):
    await dpytest.message("/img design a fight club logo")
    assert not dpytest.verify().message().nothing()