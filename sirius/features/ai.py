import io
import asyncio
import aiohttp

from openai import OpenAI
from discord import File
from discord.ext import commands

from yaml import safe_load

from sirius.constants import (
    OPENAI_API_KEY,
    NAME,
    INSTRUCTIONS
)


client = OpenAI(
    api_key=OPENAI_API_KEY
)


class AI(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Initialized AI feature.")

    @commands.command(name="ai")
    async def _ai(self, ctx: commands.Context, *, message: str):

        if ctx.author.name == NAME:
            await ctx.send("I am not supposed to answer to my own questions."); return

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": INSTRUCTIONS.replace("\n", " ")},
                {"role": "user", "content": message}
            ]
        )

        await ctx.send(response.choices[0].message.content)

    @commands.command(name="img")
    async def _img(self, ctx: commands.Context, *, message: str):

        await ctx.defer()

        try:
            response = client.images.generate(
                model="dall-e-3",
                prompt=message,
                size="1024x1024",
                quality="standard",
                n=1,
                response_format="url"
            )

            if response.data[0]:
                image_url = response.data[0].url
                async with aiohttp.ClientSession() as session:
                    async with session.get(image_url) as resp:
                        if resp.status != 200:
                            return await ctx.send("Could not download the file..")
                        data = io.BytesIO(await resp.read())
                        await ctx.send(file=File(data, "image.png"))

        except Exception as exc:
            print(f"An error occurred: {exc}")
            await ctx.send("An error occurred.")