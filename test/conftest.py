import pathlib

import pytest_asyncio

import discord
import discord.ext.commands as commands
import discord.ext.test as dpytest

from discord.client import _LoopSentinel


@pytest_asyncio.fixture
async def bot():
    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True

    bot = commands.Bot(
        command_prefix="/",
        intents=intents
    )
    
    await bot._async_setup_hook()
    await bot.load_extension("dcbot.features")

    dpytest.configure(bot)

    yield bot

    await dpytest.empty_queue()


def pytest_sessionfinish(session, exitstatus):
    print("\n--------------------------------\nRemoving dpytest_*.dat files.")
    files = pathlib.Path(".").glob("dpytest_*.dat")
    for file in files:
        try: file.unlink()
        except Exception: print(f"An error occured while deleting a file: {file}")