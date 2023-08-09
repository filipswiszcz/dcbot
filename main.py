import os
import asyncio
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

discord.opus._load_default()

bot = commands.Bot(
    command_prefix="/",
    intents=intents
)

async def load_extensions():
    for filename in os.listdir("./models"):
        if filename.endswith(".py"):
            await bot.load_extension(f"models.{filename[:-3]}")

async def main():
    async with bot:
        await load_extensions()
        await bot.start("__KEY__")

asyncio.run(main())
