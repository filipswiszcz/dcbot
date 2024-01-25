import asyncio

from typing import Optional
from yaml import safe_load

from constants import OPENAI_API_KEY

from openai import OpenAI
from discord.ext import commands

client = OpenAI(
    api_key=OPENAI_API_KEY
)

class AI(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.__pre_prompt = self.__load_pre_prompt()

    def __load_pre_prompt(self):
        with open("src/pre_prompt_sirius.yml") as f:
            temp = safe_load(f.read())
        return temp

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Initialized AI feature.")

    @commands.command(name="ai")
    async def _ai(self, ctx: commands.Context, *, message: str):
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": self.__pre_prompt["instructions"].replace("\n", " ")},
                {"role": "user", "content": message}
            ]
        )
        await ctx.send(response.choices[0].message.content)


async def setup(bot):
    await bot.add_cog(AI(bot))