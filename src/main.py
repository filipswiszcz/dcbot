import os
import asyncio
import openai
import discord

from discord.ext import commands

from constants import (
    DISCORD_BOT_TOKEN,
    BOT_INVITE_URL
)

intents = discord.Intents.default()
intents.message_content = True

discord.opus._load_default()

bot = commands.Bot(
    command_prefix="/",
    intents=intents
)

print(f"\nInvite URL: {BOT_INVITE_URL}\n")

async def load_extensions():
    for filename in os.listdir("./src/features"):
        if filename.endswith(".py"):
            await bot.load_extension(f"features.{filename[:-3]}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start(DISCORD_BOT_TOKEN)

asyncio.run(main())