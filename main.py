import os
import asyncio
import openai
import discord

from discord.ext import commands

from sirius.constants import (
    DISCORD_BOT_TOKEN,
    BOT_INVITE_URL
)


intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(
    command_prefix="/",
    intents=intents
)


async def load_extensions():
    #for filename in os.listdir("./sirius/features"):
        #if filename.endswith(".py"):
            #await bot.load_extension(f"features.{filename[:-3]}")
    await bot.load_extension("sirius.features")


async def main():
    async with bot:
        await load_extensions()
        await bot.start(DISCORD_BOT_TOKEN)
        

if __name__ == "__main__":
    print(f"\nInvite URL: {BOT_INVITE_URL}\n")
    try: asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping...")